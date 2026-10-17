"""Минимальный клиент Supabase (Auth + PostgREST) на стандартной библиотеке."""
import json
import threading
import urllib.error
import urllib.parse
import urllib.request

from .config import SUPABASE_KEY, SUPABASE_URL

PAGE = 1000  # лимит строк PostgREST по умолчанию


class ApiError(RuntimeError):
    def __init__(self, message, status=0):
        super().__init__(message)
        self.status = status


def enc(value):
    return urllib.parse.quote(str(value), safe="")


def _qs(params):
    # Скобки, запятые, точки, '*' и ':' оставляем как есть — они нужны синтаксису PostgREST.
    return "&".join(f"{k}={urllib.parse.quote(str(v), safe='(),.*:')}" for k, v in params.items())


class Supabase:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.user = {}
        self.on_tokens = None  # callback(refresh_token|None): сохранить/сбросить сессию
        self._lock = threading.Lock()

    @property
    def is_authenticated(self):
        return bool(self.access_token)

    # ------------------------------------------------------------------ низкий уровень
    def request(self, path, method="GET", body=None, headers=None, _retry=True):
        h = {"Content-Type": "application/json"}
        if headers:
            h.update(headers)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        raw = self._send(path, method, data, h, _retry)
        return json.loads(raw) if raw else {}

    def _send(self, path, method, data, headers, _retry=True, timeout=25):
        """Один HTTP-вызов к Supabase с авторизацией и однократным обновлением токена. Возвращает текст ответа."""
        h = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {self.access_token or SUPABASE_KEY}"}
        h.update(headers or {})
        req = urllib.request.Request(SUPABASE_URL + path, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw)
            except Exception:
                detail = raw
            if isinstance(detail, dict):
                msg = detail.get("message") or detail.get("msg") or detail.get("error_description") or detail.get("error")
            else:
                msg = str(detail)
            if _retry and self.refresh_token and e.code in (401, 403) and "jwt" in str(msg).lower():
                if self._refresh():
                    h2 = dict(headers or {})
                    h2.pop("Authorization", None)
                    return self._send(path, method, data, h2, _retry=False, timeout=timeout)
            raise ApiError(msg or f"HTTP {e.code}", e.code)
        except urllib.error.URLError as e:
            raise ApiError(f"Нет соединения с сервером: {e.reason}")
        except Exception as e:  # noqa: BLE001
            raise ApiError(f"Ошибка соединения: {e}")

    def _tokens_changed(self):
        if self.on_tokens:
            try:
                self.on_tokens(self.refresh_token)
            except Exception:  # noqa: BLE001
                pass

    def _refresh(self):
        with self._lock:
            try:
                data = self.request("/auth/v1/token?grant_type=refresh_token", "POST",
                                    {"refresh_token": self.refresh_token}, _retry=False)
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token") or self.refresh_token
                self._tokens_changed()
                return bool(self.access_token)
            except ApiError:
                return False

    # ------------------------------------------------------------------ авторизация
    def auth_login(self, email, password):
        data = self.request("/auth/v1/token?grant_type=password", "POST", {"email": email, "password": password})
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        self.user = data.get("user") or {}
        self._tokens_changed()
        return data

    def restore_session(self, refresh_token):
        """Автовход: обменивает сохранённый refresh-токен на новую сессию (токен при этом ротируется)."""
        self.access_token = None
        data = self.request("/auth/v1/token?grant_type=refresh_token", "POST", {"refresh_token": refresh_token}, _retry=False)
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token") or refresh_token
        self.user = data.get("user") or {}
        self._tokens_changed()
        return data

    def auth_register(self, email, password, username, display_name):
        return self.request("/auth/v1/signup", "POST", {
            "email": email, "password": password,
            "data": {"username": username, "display_name": display_name or username},
        })

    def auth_recover(self, email):
        return self.request("/auth/v1/recover", "POST", {"email": email})

    def auth_logout(self):
        if self.access_token:
            try:
                self.request("/auth/v1/logout", "POST", _retry=False)
            except ApiError:
                pass
        self.access_token = None
        self.refresh_token = None
        self.user = {}
        self._tokens_changed()

    # ------------------------------------------------------------------ Storage
    def public_url(self, bucket, path):
        return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{urllib.parse.quote(path, safe='/')}"

    def upload_object(self, bucket, path, data, content_type):
        """Загружает файл в Storage (нужен вход; права задаёт RLS на storage.objects)."""
        self._send(f"/storage/v1/object/{bucket}/{urllib.parse.quote(path, safe='/')}", "POST", data,
                   {"Content-Type": content_type, "x-upsert": "false", "cache-control": "max-age=31536000"}, timeout=90)
        return self.public_url(bucket, path)

    def delete_objects(self, bucket, paths):
        if not paths:
            return
        body = json.dumps({"prefixes": list(paths)}).encode("utf-8")
        self._send(f"/storage/v1/object/{bucket}", "DELETE", body, {"Content-Type": "application/json"})

    # ------------------------------------------------------------------ PostgREST
    def table(self, table, select="*", filters=None, order=None, limit=None, offset=None):
        params = {"select": select}
        if filters:
            params.update(filters)
        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        if offset:
            params["offset"] = str(offset)
        return self.request(f"/rest/v1/{table}?" + _qs(params))

    def table_all(self, table, select="*", filters=None, order=None, max_rows=20000):
        """Постранично забирает все строки (обход лимита 1000)."""
        rows, offset = [], 0
        while offset < max_rows:
            chunk = self.table(table, select, filters, order, PAGE, offset)
            rows.extend(chunk)
            if len(chunk) < PAGE:
                break
            offset += PAGE
        return rows

    def insert(self, table, rows, select="*", upsert_on=None, ignore_duplicates=False):
        params = {"select": select}
        prefer = "return=representation"
        if upsert_on:
            params["on_conflict"] = upsert_on
            prefer += ",resolution=" + ("ignore-duplicates" if ignore_duplicates else "merge-duplicates")
        return self.request(f"/rest/v1/{table}?" + _qs(params), "POST", rows, headers={"Prefer": prefer})

    def update(self, table, filters, values, select="*", expect=False):
        params = {"select": select}
        params.update(filters)
        res = self.request(f"/rest/v1/{table}?" + _qs(params), "PATCH", values, headers={"Prefer": "return=representation"})
        if expect and not res:
            raise ApiError("Не сохранено: нет прав (выполните migration_v2_2.sql в Supabase) или запись удалена.", 403)
        return res

    def delete(self, table, filters, expect=False):
        """expect=True: если ни одна строка не удалена (нет прав по RLS или уже удалена) — ApiError, а не тихий «успех»."""
        res = self.request(f"/rest/v1/{table}?" + _qs(filters), "DELETE", headers={"Prefer": "return=representation"})
        if expect and not res:
            raise ApiError("Не удалено: нет прав (выполните migration_v2_2.sql в Supabase) или запись уже удалена.", 403)
        return res

    def rpc(self, fn, payload=None):
        return self.request(f"/rest/v1/rpc/{fn}", "POST", payload or {})
