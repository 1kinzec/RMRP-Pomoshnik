-- RMRP Помощник — release security migration 1.1.1
-- Выполнить ПОСЛЕ основного rmrp_database.sql в Supabase SQL Editor.

-- Безопасная проверка роли текущего пользователя без рекурсивной RLS-проверки.
create or replace function public.my_profile_role()
returns public.user_role
language sql
stable
security definer
set search_path = public
as $$
  select role from public.profiles where id = auth.uid();
$$;

create or replace function public.my_profile_status()
returns public.user_status
language sql
stable
security definer
set search_path = public
as $$
  select status from public.profiles where id = auth.uid();
$$;

create or replace function public.my_profile_premium()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select premium from public.profiles where id = auth.uid();
$$;

-- Администратор не может повысить себя, другого администратора или Основателя.
create or replace function public.can_manage_profile(target_id uuid, new_role public.user_role)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select case
    when public.is_founder() then true
    when public.is_admin_or_founder() then
      exists (
        select 1 from public.profiles target
        where target.id = target_id
          and target.role not in ('FOUNDER','ADMIN')
      )
      and new_role in ('MODERATOR','PREMIUM','USER')
    else false
  end;
$$;

-- Убираем старые конфликтующие правила изменения профилей.
drop policy if exists "profiles_update_own" on public.profiles;
drop policy if exists "profiles_admin_update" on public.profiles;
drop policy if exists "profiles_self_update" on public.profiles;
drop policy if exists "profiles_admin_or_founder_update" on public.profiles;

-- Обычный пользователь может менять только безопасные поля своего профиля.
-- Роль, статус и Premium нельзя изменить самому себе.
create policy "profiles_self_update"
on public.profiles for update
to authenticated
using (id = auth.uid())
with check (
  id = auth.uid()
  and role = public.my_profile_role()
  and status = public.my_profile_status()
  and premium = public.my_profile_premium()
);

-- Админ/Основатель управляет чужими профилями по иерархии.
create policy "profiles_admin_or_founder_update"
on public.profiles for update
to authenticated
using (public.can_manage_profile(id, role))
with check (public.can_manage_profile(id, role));

-- Защита профиля Основателя на уровне БД.
create or replace function public.protect_founder_profile()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if old.role = 'FOUNDER' and not public.is_founder() then
    new.role := old.role;
    new.status := old.status;
    new.premium := old.premium;
  end if;
  return new;
end;
$$;

drop trigger if exists protect_founder_profile on public.profiles;
create trigger protect_founder_profile
before update on public.profiles
for each row execute procedure public.protect_founder_profile();

insert into public.app_settings(key, value)
values
  ('app_name', 'RMRP Помощник'),
  ('app_version', '1.1.1'),
  ('role_hierarchy', 'FOUNDER > ADMIN > MODERATOR > PREMIUM > USER')
on conflict (key) do update set value = excluded.value, updated_at = now();
