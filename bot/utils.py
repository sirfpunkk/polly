from datetime import datetime
from typing import List, Dict

def format_listing(listing: Dict) -> str:
    return (
        f"🏠 <b>{listing['source'].upper()}</b>\n"
        f"💰 <b>{listing['price']:,}₽</b>\n"
        f"📍 <b>{listing['district']}</b>\n"
        f"📏 <b>{listing['area']}м²</b> ({listing['rooms']}к)\n"
        f"🏢 <b>{listing['floor']}/{listing['total_floors']} этаж</b>\n"
        f"🕒 <i>{listing['posted_at'].strftime('%d.%m.%Y %H:%M')}</i>"
    )

def chunk_list(items: List, size: int) -> List[List]:
    return [items[i:i + size] for i in range(0, len(items), size)]
