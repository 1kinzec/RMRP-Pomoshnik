-- RMRP Помощник 2.4: сводка админ-панели.
-- Выполнить в Supabase → SQL Editor. Безопасно запускать повторно.

-- Админ и основатель видят обезличенную статистику популярных поисков и вопросов к ИИ.
-- В приложении показываются только тексты запросов, без имён авторов.
drop policy if exists "search_history_admin_read" on public.search_history;
create policy "search_history_admin_read" on public.search_history for select to authenticated
using (public.is_admin_or_founder());

drop policy if exists "ai_history_admin_read" on public.ai_history;
create policy "ai_history_admin_read" on public.ai_history for select to authenticated
using (public.is_admin_or_founder());
