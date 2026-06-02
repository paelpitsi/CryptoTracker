"""Export service for exporting data to CSV and JSON."""

import csv
import json
import io
from datetime import datetime, date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from cryptotracker.server.models.query_history import QueryHistory, QueryHistoryItem
from cryptotracker.server.models.watchlist import Watchlist, WatchlistItem
from cryptotracker.server.external.frankfurter import FrankfurterClient
from cryptotracker.server.external.coingecko import CoinGeckoClient
from cryptotracker.server.models.currency import Currency
from cryptotracker.common.exceptions import WatchlistNotFoundError
from cryptotracker.common.logger import logger
from decimal import Decimal


class ExportService:
    """Service for exporting data."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.frankfurter = FrankfurterClient()
        self.coingecko = CoinGeckoClient()
    
    async def export_history(
        self,
        format: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        command_type: Optional[str] = None
    ) -> tuple[str, str, str]:
        """Export query history to CSV or JSON."""
        
        try:
            # Build query
            query = select(QueryHistory).options(selectinload(QueryHistory.items))
            
            if command_type:
                query = query.where(QueryHistory.command_type == command_type)
            
            if date_from:
                query = query.where(QueryHistory.created_at >= datetime.combine(date_from, datetime.min.time()))
            
            if date_to:
                query = query.where(QueryHistory.created_at <= datetime.combine(date_to, datetime.max.time()))
            
            query = query.order_by(QueryHistory.created_at.desc())
            
            result = await self.session.execute(query)
            queries = result.scalars().all()
            
            # Prepare data
            data = []
            for q in queries:
                for item in q.items:
                    data.append({
                        "id": q.id,
                        "created_at": q.created_at.isoformat(),
                        "command_type": q.command_type,
                        "base_currency": item.base_currency,
                        "target_currency": item.target_currency,
                        "rate": str(item.rate),
                        "type": item.currency_type,
                        "change_24h": str(item.change_24h) if item.change_24h else ""
                    })
            
            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            
            if format == "csv":
                filename = f"history_{timestamp}.csv"
                content_type = "text/csv"
                
                output = io.StringIO()
                if data:
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                content = output.getvalue()
                
            else:  # json
                filename = f"history_{timestamp}.json"
                content_type = "application/json"
                
                export_data = {
                    "export_date": datetime.utcnow().isoformat(),
                    "total_records": len(data),
                    "data": data
                }
                content = json.dumps(export_data, indent=2)
            
            return content, filename, content_type
            
        except Exception as e:
            logger.error(f"Error in export_history: {e}")
            raise
    
    async def export_watchlist(
        self,
        watchlist_id: int,
        format: str,
        include_rates: bool = True
    ) -> tuple[str, str, str]:
        """Export watchlist to CSV or JSON."""
        
        try:
            # Get watchlist
            result = await self.session.execute(
                select(Watchlist)
                .where(Watchlist.id == watchlist_id)
                .options(selectinload(Watchlist.items))
            )
            watchlist = result.scalar_one_or_none()
            
            if not watchlist:
                raise WatchlistNotFoundError(f"Watchlist with ID {watchlist_id} not found")
            
            # Prepare data
            data = []
            for item in watchlist.items:
                item_data = {
                    "base_currency": item.base_currency,
                    "target_currency": item.target_currency,
                    "type": item.currency_type,
                    "added_at": item.added_at.isoformat()
                }
                
                if include_rates:
                    current_rate = None
                    change_24h = None
                    
                    try:
                        if item.currency_type == "fiat":
                            rates = await self.frankfurter.get_latest_rates(
                                item.base_currency,
                                [item.target_currency]
                            )
                            if item.target_currency in rates:
                                current_rate = rates[item.target_currency]
                        else:
                            # Crypto
                            currency = await self._get_currency(item.base_currency)
                            if currency.coingecko_id:
                                prices = await self.coingecko.get_simple_price(
                                    ids=[currency.coingecko_id],
                                    vs_currencies=[item.target_currency.lower()],
                                    include_24h_change=True
                                )
                                if currency.coingecko_id in prices:
                                    price_data = prices[currency.coingecko_id]
                                    current_rate = price_data.get(item.target_currency.lower())
                                    change = price_data.get(f"{item.target_currency.lower()}_24h_change")
                                    if change:
                                        change_24h = change
                    except Exception as e:
                        logger.warning(f"Failed to get rate for {item.base_currency}/{item.target_currency}: {e}")
                    
                    item_data["current_rate"] = str(current_rate) if current_rate else ""
                    item_data["change_24h"] = str(change_24h) if change_24h else ""
                
                data.append(item_data)
            
            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
            
            if format == "csv":
                filename = f"watchlist_{watchlist.name}_{timestamp}.csv"
                content_type = "text/csv"
                
                output = io.StringIO()
                if data:
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                content = output.getvalue()
                
            else:  # json
                filename = f"watchlist_{watchlist.name}_{timestamp}.json"
                content_type = "application/json"
                
                export_data = {
                    "watchlist": {
                        "id": watchlist.id,
                        "name": watchlist.name,
                        "description": watchlist.description
                    },
                    "export_date": datetime.utcnow().isoformat(),
                    "items": data
                }
                content = json.dumps(export_data, indent=2)
            
            return content, filename, content_type
            
        except WatchlistNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error in export_watchlist: {e}")
            raise
    
    async def _get_currency(self, code: str) -> Currency:
        """Get currency by code."""
        
        result = await self.session.execute(
            select(Currency).where(Currency.code == code.upper())
        )
        currency = result.scalar_one_or_none()
        
        if not currency:
            from cryptotracker.common.exceptions import CurrencyNotFoundError
            raise CurrencyNotFoundError(f"Currency '{code}' not found")
        
        return currency
