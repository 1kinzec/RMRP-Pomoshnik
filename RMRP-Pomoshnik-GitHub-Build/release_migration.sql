-- RMRP Помощник — release security migration 1.1.0
-- Выполнить ПОСЛЕ основного rmrp_database.sql в Supabase SQL Editor.

-- Безопасное управление ролями: администратор не может создать/изменить FOUNDER или ADMIN.
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

drop policy if exists "profiles_admin_update" on public.profiles;
create policy "profiles_admin_update"
on public.profiles for update
to authenticated
using (
  public.can_manage_profile(id, role)
)
with check (
  public.can_manage_profile(id, role)
);

-- Основатель всегда остаётся активным и не может быть изменён администратором.
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

-- Представление роли для клиента/отладки.
insert into public.app_settings(key, value)
values
  ('app_name', 'RMRP Помощник'),
  ('app_version', '1.1.0'),
  ('role_hierarchy', 'FOUNDER > ADMIN > MODERATOR > PREMIUM > USER')
on conflict (key) do update set value = excluded.value, updated_at = now();
