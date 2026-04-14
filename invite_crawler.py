import asyncio
import re
import random
import time
import os
import argparse
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from telethon.sync import TelegramClient
from telethon import functions, types
from colorama import init

init(autoreset=True)

# --- [КОНФИГУРАЦИЯ] ---
API_ID = 1234567          
API_HASH = 'your_hash'
console = Console()

INVITE_REGEX = r'(?:https?://)?t\.me/(?:joinchat/|\+)[a-zA-Z0-9_-]+'
ADMIN_REGEX = r'@[\w\d_]+'

async def get_admin_info(client, username):
    try:
        await asyncio.sleep(random.uniform(1.5, 2.5))
        user = await client.get_entity(username)
        if isinstance(user.status, types.UserStatusOnline):
            status = "Online"
        elif isinstance(user.status, types.UserStatusOffline):
            status = user.status.was_online.strftime("%Y-%m-%d %H:%M")
        else:
            status = "Recently/Hidden"
        return f"{user.id} | {status}"
    except:
        return "N/A | Hidden"

async def sniff_passive(client, link):
    try:
        invite_hash = link.split('/')[-1].replace('+', '').replace('joinchat/', '')
        await asyncio.sleep(random.uniform(3.0, 5.0))
        result = await client(functions.messages.CheckChatInviteRequest(hash=invite_hash))
        
        if isinstance(result, types.ChatInvite):
            about_text = result.about if result.about else ""
            contacts = list(set(re.findall(ADMIN_REGEX, about_text)))
            admin_details = []
            for adm in contacts:
                intel = await get_admin_info(client, adm)
                admin_details.append(f"{adm} ({intel})")
            
            return {
                "title": result.title,
                "members": result.participants_count,
                "scam": "[bold red]SCAM[/bold red]" if result.scam or result.fake else "[green]Clean[/green]",
                "admins": " | ".join(admin_details) if admin_details else "None",
                "link": link
            }
    except:
        return None

async def process_links(client, links, source_name):
    table = Table(title=f"Results: {source_name}", title_style="bold magenta", border_style="dim")
    table.add_column("Invite Link", style="blue")
    table.add_column("Members", style="green")
    table.add_column("Admin Intel (ID | Last Seen)", style="cyan")

    report_lines = []
    with Progress(transient=True) as progress:
        task = progress.add_task("[magenta]Analyzing...", total=len(links))
        for link in links:
            info = await sniff_passive(client, link)
            if info:
                table.add_row(info['link'], str(info['members']), info['admins'])
                report_lines.append(f"Link: {info['link']} | admin_intel: {info['admins']} | title: {info['title']}")
            progress.update(task, advance=1)

    console.print(table)
    
    filename = f"intel_{datetime.now().strftime('%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    console.print(f"\n[dim]Saved to: {filename}[/dim]")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", help="Username канала для сканирования")
    parser.add_argument("-f", "--file", help="Путь к файлу со ссылками")
    parser.add_argument("-l", "--limit", type=int, default=500)
    args = parser.parse_args()

    async with TelegramClient('crawler_session', API_ID, API_HASH) as client:
        links_to_check = set()
        
        if args.target:
            async for message in client.iter_messages(args.target, limit=args.limit):
                if message.text:
                    found = re.findall(INVITE_REGEX, message.text)
                    for l in found:
                        links_to_check.add(l if l.startswith('http') else f"https://{l}")
            source = args.target
        elif args.file:
            with open(args.file, 'r') as f:
                for line in f:
                    if "t.me/" in line:
                        links_to_check.add(line.strip())
            source = args.file
        else:
            console.print("[red]Используй -t или -f. Справка: --help[/red]")
            return

        if links_to_check:
            await process_links(client, list(links_to_check), source)
        else:
            console.print("[yellow]Ссылки не найдены.[/yellow]")

if __name__ == "__main__":
    asyncio.run(main())
