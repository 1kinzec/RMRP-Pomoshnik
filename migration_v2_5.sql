-- ============================================================
-- RMRP Помощник 2.5: краткие памятки, фото, команда, цвета ролей
-- Выполнить в Supabase → SQL Editor ПОСЛЕ migration_v2_3.sql. Скрипт можно запускать повторно.
-- ============================================================

-- 1. Кто может публиковать памятки (Основатель и Администраторы).
--    Чтобы разрешить и модераторам — добавьте 'MODERATOR' в список ролей ниже.
create or replace function public.can_publish_memos()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid()
      and role in ('FOUNDER','ADMIN')
      and status = 'ACTIVE'
  );
$$;
revoke all on function public.can_publish_memos() from public;
grant execute on function public.can_publish_memos() to authenticated;

-- 2. Таблица памяток
create table if not exists public.memos (
  id uuid primary key default gen_random_uuid(),
  author_id uuid references public.profiles(id) on delete set null,
  title text not null check (char_length(btrim(title)) between 1 and 120),
  content text not null default '' check (char_length(content) <= 8000),
  tags text[] not null default '{}' check (cardinality(tags) <= 8),
  images text[] not null default '{}' check (cardinality(images) <= 8),
  pinned boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists memos_created_idx on public.memos (pinned desc, created_at desc);

drop trigger if exists memos_updated_at on public.memos;
create trigger memos_updated_at before update on public.memos
  for each row execute function public.set_updated_at();

alter table public.memos enable row level security;

drop policy if exists "memos_read" on public.memos;
create policy "memos_read" on public.memos for select to anon, authenticated using (true);

drop policy if exists "memos_publish_insert" on public.memos;
create policy "memos_publish_insert" on public.memos for insert to authenticated
  with check (public.can_publish_memos() and author_id = auth.uid());

drop policy if exists "memos_publish_update" on public.memos;
create policy "memos_publish_update" on public.memos for update to authenticated
  using (public.can_publish_memos()) with check (public.can_publish_memos());

drop policy if exists "memos_publish_delete" on public.memos;
create policy "memos_publish_delete" on public.memos for delete to authenticated
  using (public.can_publish_memos());

-- 3. Лента памяток с данными автора (профили закрыты RLS, поэтому через security definer-функцию).
--    Отдаёт только имя, роль и аватар автора.
create or replace function public.memos_feed(p_limit int default 200)
returns table (
  id uuid, title text, content text, tags text[], images text[], pinned boolean,
  created_at timestamptz, updated_at timestamptz,
  author_id uuid, author_name text, author_role text, author_avatar text
)
language sql
stable
security definer
set search_path = public
as $$
  select m.id, m.title, m.content, m.tags, m.images, m.pinned, m.created_at, m.updated_at,
         m.author_id, coalesce(nullif(p.display_name, ''), p.username), p.role::text, p.avatar_url
  from public.memos m
  left join public.profiles p on p.id = m.author_id
  order by m.pinned desc, m.created_at desc
  limit least(greatest(coalesce(p_limit, 200), 1), 500);
$$;
revoke all on function public.memos_feed(int) from public;
grant execute on function public.memos_feed(int) to anon, authenticated;

-- 4. Хранилище для фото (публичное чтение; загрузка и удаление — только публикующим)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('memo-images', 'memo-images', true, 5242880, array['image/jpeg','image/png','image/webp','image/gif'])
on conflict (id) do update
  set public = true, file_size_limit = excluded.file_size_limit, allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "memo_images_read" on storage.objects;
create policy "memo_images_read" on storage.objects for select to anon, authenticated
  using (bucket_id = 'memo-images');

drop policy if exists "memo_images_insert" on storage.objects;
create policy "memo_images_insert" on storage.objects for insert to authenticated
  with check (bucket_id = 'memo-images' and public.can_publish_memos());

drop policy if exists "memo_images_delete" on storage.objects;
create policy "memo_images_delete" on storage.objects for delete to authenticated
  using (bucket_id = 'memo-images' and public.can_publish_memos());

-- 5. «Команда приложения»: видна всем (в том числе гостям). Только имя, аватар, роль и время последнего визита.
create or replace function public.app_team()
returns table (id uuid, username text, display_name text, avatar_url text, role text, last_seen_at timestamptz)
language sql
stable
security definer
set search_path = public
as $$
  select p.id, p.username, p.display_name, p.avatar_url, p.role::text, p.last_seen_at
  from public.profiles p
  where p.status = 'ACTIVE' and p.role in ('FOUNDER','ADMIN','MODERATOR')
  order by case p.role when 'FOUNDER' then 0 when 'ADMIN' then 1 else 2 end,
           lower(coalesce(nullif(p.display_name, ''), p.username));
$$;
revoke all on function public.app_team() from public;
grant execute on function public.app_team() to anon, authenticated;

-- 6. Цвета ролей: общая настройка (меняет Основатель в «Настройках»). Читать её могут и гости.
insert into public.app_settings (key, value) values ('role_colors', '{}')
on conflict (key) do nothing;

drop policy if exists "settings_role_colors_anon" on public.app_settings;
create policy "settings_role_colors_anon" on public.app_settings for select to anon
  using (key = 'role_colors');

update public.app_settings set value = '2.5.0', updated_at = now() where key = 'app_version';
