import asyncio
import re
import random
import time
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from telethon.sync import TelegramClient
from telethon import functions, types
from telethon.errors import FloodWaitError
from colorama import init

init(autoreset=True)

# --- [КОНФИГУРАЦИЯ] ---
API_ID = 1234567          # Замени на свой
API_HASH = 'your_hash'    # Замени на свой
console = Console()

# Регулярки для поиска инвайтов и юзернеймов
INVITE_REGEX = r'(?:https?://)?t\.me/(?:joinchat/|\+)[a-zA-Z0-9_-]+'
ADMIN_REGEX = r'@[\w\d_]+'

async def get_admin_info(client, username):
    """Deep Check: Получение ID и статуса активности админа"""
    try:
        await asyncio.sleep(random.uniform(1.2, 2.5)) # Защита от Flood
        user = await client.get_entity(username)
        
        # Определяем статус последнего входа
        if isinstance(user.status, types.UserStatusOnline):
            status = "Online"
        elif isinstance(user.status, types.UserStatusOffline):
            status = user.status.was_online.strftime("%Y-%m-%d %H:%M")
        else:
            status = "Recently/Hidden"
            
        return f"{user.id} | {status}"
    except Exception:
        return "N/A | Hidden"

async def sniff_passive(client, link):
    """Passive Analysis: Сбор данных о чате без вступления + поиск админов"""
    try:
        invite_hash = link.split('/')[-1].replace('+', '').replace('joinchat/', '')
        await asyncio.sleep(random.uniform(3.0, 5.0)) # Пауза для беспалевности
        result = await client(functions.messages.CheckChatInviteRequest(hash=invite_hash))
        
        if isinstance(result, types.ChatInvite):
            about_text = result.about if result.about else ""
            # Поиск всех @username в описании
            contacts = list(set(re.findall(ADMIN_REGEX, about_text)))
            
            admin_details = []
            for adm in contacts:
                intel = await get_admin_info(client, adm)
                admin_details.append(f"{adm} ({intel})")
            
            admin_str = " | ".join(admin_details) if admin_details else "None"
            
            return {
                "title": result.title,
                "members": result.participants_count,
                "scam": "[bold red]SCAM[/bold red]" if result.scam or result.fake else "[green]Clean[/green]",
                "admins": admin_str,
                "link": link
            }
    except Exception:
        return None

async def crawl_and_sniff(target_chat, limit):
    console.print(f"\n[bold red]─── OSINT CRAWLER v6.3 | ADMIN INTELLIGENCE ───[/bold red]", justify="center")
    console.print(f"[dim]Time: {time.asctime()}[/dim]\n", justify="center")
    
    async with TelegramClient('crawler_session', API_ID, API_HASH) as client:
        found_links = set()
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), transient=True) as progress:
            task1 = progress.add_task(f"[cyan]Scraping {target_chat}...", total=limit)
            async for message in client.iter_messages(target_chat, limit=limit):
                if message.text:
                    links = re.findall(INVITE_REGEX, message.text)
                    for l in links:
                        # Форматируем ссылку в полный URL
                        clean_link = l if l.startswith('http') else f"https://{l}"
                        found_links.add(clean_link)
                progress.update(task1, advance=1)

        if not found_links:
            console.print("[bold yellow][!] Инвайтов в истории не обнаружено.[/bold yellow]")
            return

        console.print(f"[bold green][+] Найдено уникальных приватных ссылок: {len(found_links)}[/bold green]\n")

        # Настройка таблицы вывода на экран
        table = Table(title=f"Target: {target_chat}", title_style="bold magenta", border_style="dim")
        table.add_column("Invite Link", style="blue")
        table.add_column("Members", style="green")
        table.add_column("Admin Intel (ID | Last Seen)", style="cyan")

        report_lines = []

        with Progress(transient=True) as progress:
            task2 = progress.add_task("[magenta]Extracting Intelligence...", total=len(found_links))
            for link in found_links:
                info = await sniff_passive(client, link)
                if info:
                    table.add_row(info['link'], str(info['members']), info['admins'])
                    # Запись в лог по твоему стилю
                    report_lines.append(f"Link: {info['link']} | admin_intel: {info['admins']} | title: {info['title']}")
                progress.update(task2, advance=1)

        console.print(table)
        
        # Сохранение лога
        filename = f"intel_{str(target_chat).replace('@','').replace('/','')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"--- OSINT INTEL REPORT | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f.write(f"Source: {target_chat}\n\n")
            f.write("\n".join(report_lines))
        
        console.print(f"\n[bold white]Logs saved to:[/bold white] [underline]{filename}[/underline]\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OSINT Admin Intelligence Crawler")
    parser.add_argument("-t", "--target", help="Username источника (напр. @group_name)")
    parser.add_argument("-l", "--limit", type=int, default=500, help="Лимит сообщений для поиска")
    args = parser.parse_args()

    if args.target:
        try:
            asyncio.run(crawl_and_sniff(args.target, args.limit))
        except KeyboardInterrupt:
            console.print("\n[bold red][!] Прервано пользователем.[/bold red]")
    else:
        console.print("[bold red]Укажите цель:[/bold red] python3 script.py -t @target")
