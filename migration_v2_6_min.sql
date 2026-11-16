create extension if not exists pgcrypto;

create or replace function public.can_edit_account(target_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select case
    when auth.uid() is null then false
    when public.is_founder() then true
    when public.is_admin_or_founder() then
      target_id = auth.uid()
      or exists (
        select 1 from public.profiles t
        where t.id = target_id and t.role not in ('FOUNDER', 'ADMIN')
      )
    else false
  end;
$$;

create or replace function public.admin_set_password(p_user_id uuid, p_password text)
returns void
language plpgsql
security definer
set search_path = public, auth, extensions
as $$
begin
  if not public.can_edit_account(p_user_id) then
    raise exception 'Недостаточно прав для смены пароля этого аккаунта' using errcode = '42501';
  end if;
  if p_password is null or char_length(p_password) < 6 then
    raise exception 'Пароль должен быть не короче 6 символов' using errcode = '22023';
  end if;
  if octet_length(p_password) > 72 then
    raise exception 'Пароль слишком длинный (максимум 72 байта)' using errcode = '22023';
  end if;

  update auth.users
     set encrypted_password = crypt(p_password, gen_salt('bf')),
         updated_at = now()
   where id = p_user_id;
  if not found then
    raise exception 'Пользователь не найден' using errcode = 'P0002';
  end if;

  if p_user_id <> auth.uid() then
    begin
      delete from auth.sessions where user_id = p_user_id;
    exception when undefined_table then
      null;
    end;
  end if;

  insert into public.audit_logs (user_id, action, target_type, target_id, details)
  values (auth.uid(), 'ACCOUNT_PASSWORD_CHANGED', 'profile', p_user_id::text, jsonb_build_object('field', 'password'));
end;
$$;

create or replace function public.admin_set_email(p_user_id uuid, p_email text)
returns void
language plpgsql
security definer
set search_path = public, auth, extensions
as $$
declare
  v_email text := lower(btrim(coalesce(p_email, '')));
  v_old text;
begin
  if not public.can_edit_account(p_user_id) then
    raise exception 'Недостаточно прав для смены email этого аккаунта' using errcode = '42501';
  end if;
  if v_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' or char_length(v_email) > 254 then
    raise exception 'Некорректный email' using errcode = '22023';
  end if;
  if exists (select 1 from auth.users where lower(email) = v_email and id <> p_user_id) then
    raise exception 'Этот email уже занят другим аккаунтом' using errcode = '23505';
  end if;

  select email into v_old from auth.users where id = p_user_id;
  if not found then
    raise exception 'Пользователь не найден' using errcode = 'P0002';
  end if;

  update auth.users
     set email = v_email,
         email_confirmed_at = coalesce(email_confirmed_at, now()),
         raw_user_meta_data = case when raw_user_meta_data ? 'email'
                                   then jsonb_set(raw_user_meta_data, '{email}', to_jsonb(v_email))
                                   else raw_user_meta_data end,
         updated_at = now()
   where id = p_user_id;

  update auth.identities
     set identity_data = jsonb_set(coalesce(identity_data, '{}'::jsonb), '{email}', to_jsonb(v_email)),
         updated_at = now()
   where user_id = p_user_id and provider = 'email';

  if p_user_id <> auth.uid() then
    begin
      delete from auth.sessions where user_id = p_user_id;
    exception when undefined_table then
      null;
    end;
  end if;

  insert into public.audit_logs (user_id, action, target_type, target_id, details)
  values (auth.uid(), 'ACCOUNT_EMAIL_CHANGED', 'profile', p_user_id::text, jsonb_build_object('old', v_old, 'new', v_email));
end;
$$;

create or replace function public.admin_set_nickname(p_user_id uuid, p_username text, p_display_name text default null)
returns void
language plpgsql
security definer
set search_path = public, auth, extensions
as $$
declare
  v_name text := btrim(coalesce(p_username, ''));
  v_disp text := nullif(btrim(coalesce(p_display_name, '')), '');
  v_old_name text;
  v_old_disp text;
begin
  if not public.can_edit_account(p_user_id) then
    raise exception 'Недостаточно прав для смены ника этого аккаунта' using errcode = '42501';
  end if;
  if v_name !~ '^[A-Za-zА-Яа-яЁё0-9_.-]{3,32}$' then
    raise exception 'Ник: 3–32 символа, буквы, цифры, _ . -' using errcode = '22023';
  end if;
  if exists (select 1 from public.profiles where lower(username) = lower(v_name) and id <> p_user_id) then
    raise exception 'Этот ник уже занят' using errcode = '23505';
  end if;

  select username, display_name into v_old_name, v_old_disp from public.profiles where id = p_user_id;
  if not found then
    raise exception 'Пользователь не найден' using errcode = 'P0002';
  end if;

  update public.profiles
     set username = v_name,
         display_name = coalesce(
           v_disp,
           case when display_name is null or display_name = '' or display_name = v_old_name then v_name else display_name end
         ),
         updated_at = now()
   where id = p_user_id;

  update auth.users
     set raw_user_meta_data = jsonb_set(coalesce(raw_user_meta_data, '{}'::jsonb), '{username}', to_jsonb(v_name)),
         updated_at = now()
   where id = p_user_id;

  insert into public.audit_logs (user_id, action, target_type, target_id, details)
  values (auth.uid(), 'ACCOUNT_NICKNAME_CHANGED', 'profile', p_user_id::text,
          jsonb_build_object('old', v_old_name, 'new', v_name, 'old_display', v_old_disp, 'new_display', v_disp));
end;
$$;

create or replace function public.admin_get_email(p_user_id uuid)
returns text
language plpgsql
stable
security definer
set search_path = public, auth
as $$
declare
  v_email text;
begin
  if not public.can_edit_account(p_user_id) then
    raise exception 'Недостаточно прав' using errcode = '42501';
  end if;
  select email::text into v_email from auth.users where id = p_user_id;
  return v_email;
end;
$$;

revoke all on function public.can_edit_account(uuid) from public, anon;
revoke all on function public.admin_set_password(uuid, text) from public, anon;
revoke all on function public.admin_set_email(uuid, text) from public, anon;
revoke all on function public.admin_set_nickname(uuid, text, text) from public, anon;
revoke all on function public.admin_get_email(uuid) from public, anon;
grant execute on function public.can_edit_account(uuid) to authenticated;
grant execute on function public.admin_set_password(uuid, text) to authenticated;
grant execute on function public.admin_set_email(uuid, text) to authenticated;
grant execute on function public.admin_set_nickname(uuid, text, text) to authenticated;
grant execute on function public.admin_get_email(uuid) to authenticated;
