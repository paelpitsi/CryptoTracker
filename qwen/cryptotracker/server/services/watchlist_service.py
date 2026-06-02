"""Watchlist service for managing currency watchlists."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from cryptotracker.server.models.watchlist import Watchlist, WatchlistItem
from cryptotracker.server.models.currency import Currency
from cryptotracker.server.external.frankfurter import FrankfurterClient
from cryptotracker.server.external.coingecko import CoinGeckoClient
from cryptotracker.server.schemas.watchlist import (
    WatchlistResponse,
    WatchlistDetailResponse,
    WatchlistListResponse,
    WatchlistItemResponse,
    WatchlistItemWithRate,
    WatchlistDeleteResponse,
    WatchlistItemDeleteResponse
)
from cryptotracker.common.exceptions import (
    WatchlistNotFoundError,
    WatchlistItemNotFoundError,
    DuplicateWatchlistError,
    DuplicateWatchlistItemError,
    CurrencyNotFoundError
)
from cryptotracker.common.logger import logger


class WatchlistService:
    """Service for managing watchlists."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.frankfurter = FrankfurterClient()
        self.coingecko = CoinGeckoClient()
    
    async def get_watchlists(self) -> WatchlistListResponse:
        """Get all watchlists."""
        
        try:
            result = await self.session.execute(
                select(Watchlist).options(selectinload(Watchlist.items))
            )
            watchlists = result.scalars().all()
            
            watchlist_responses = [
                WatchlistResponse(
                    id=w.id,
                    name=w.name,
                    description=w.description,
                    created_at=w.created_at,
                    items_count=len(w.items)
                )
                for w in watchlists
            ]
            
            return WatchlistListResponse(watchlists=watchlist_responses)
            
        except Exception as e:
            logger.error(f"Error in get_watchlists: {e}")
            raise
    
    async def get_watchlist(self, watchlist_id: int) -> WatchlistDetailResponse:
        """Get detailed watchlist with current rates."""
        
        try:
            result = await self.session.execute(
                select(Watchlist)
                .where(Watchlist.id == watchlist_id)
                .options(selectinload(Watchlist.items))
            )
            watchlist = result.scalar_one_or_none()
            
            if not watchlist:
                raise WatchlistNotFoundError(f"Watchlist with ID {watchlist_id} not found")
            
            # Get current rates for items
            items_with_rates = []
            for item in watchlist.items:
                current_rate = None
                change_24h = None
                
                try:
                    if item.currency_type == "fiat":
                        rates = await self.frankfurter.get_latest_rates(
                            item.base_currency,
                            [item.target_currency]
                        )
                        if item.target_currency in rates:
                            current_rate = Decimal(str(rates[item.target_currency]))
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
                                current_rate = Decimal(str(price_data.get(item.target_currency.lower(), 0)))
                                change = price_data.get(f"{item.target_currency.lower()}_24h_change")
                                if change:
                                    change_24h = Decimal(str(change))
                except Exception as e:
                    logger.warning(f"Failed to get rate for {item.base_currency}/{item.target_currency}: {e}")
                
                items_with_rates.append(WatchlistItemWithRate(
                    id=item.id,
                    base_currency=item.base_currency,
                    target_currency=item.target_currency,
                    type=item.currency_type,
                    current_rate=current_rate,
                    change_24h=change_24h,
                    added_at=item.added_at
                ))
            
            return WatchlistDetailResponse(
                id=watchlist.id,
                name=watchlist.name,
                description=watchlist.description,
                created_at=watchlist.created_at,
                items=items_with_rates
            )
            
        except WatchlistNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error in get_watchlist: {e}")
            raise
    
    async def create_watchlist(self, name: str, description: Optional[str] = None) -> WatchlistResponse:
        """Create a new watchlist."""
        
        try:
            # Check if watchlist with this name already exists
            result = await self.session.execute(
                select(Watchlist).where(Watchlist.name == name)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                raise DuplicateWatchlistError(f"Watchlist with name '{name}' already exists")
            
            watchlist = Watchlist(
                name=name,
                description=description
            )
            self.session.add(watchlist)
            await self.session.commit()
            await self.session.refresh(watchlist)
            
            return WatchlistResponse(
                id=watchlist.id,
                name=watchlist.name,
                description=watchlist.description,
                created_at=watchlist.created_at,
                items_count=0
            )
            
        except DuplicateWatchlistError:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in create_watchlist: {e}")
            raise
    
    async def delete_watchlist(self, watchlist_id: int) -> WatchlistDeleteResponse:
        """Delete a watchlist."""
        
        try:
            result = await self.session.execute(
                select(Watchlist)
                .where(Watchlist.id == watchlist_id)
                .options(selectinload(Watchlist.items))
            )
            watchlist = result.scalar_one_or_none()
            
            if not watchlist:
                raise WatchlistNotFoundError(f"Watchlist with ID {watchlist_id} not found")
            
            items_count = len(watchlist.items)
            await self.session.delete(watchlist)
            await self.session.commit()
            
            return WatchlistDeleteResponse(
                message=f"Watchlist '{watchlist.name}' successfully deleted",
                deleted_items_count=items_count
            )
            
        except WatchlistNotFoundError:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in delete_watchlist: {e}")
            raise
    
    async def add_item(
        self,
        watchlist_id: int,
        base_currency: str,
        target_currency: str,
        currency_type: str
    ) -> WatchlistItemResponse:
        """Add a currency pair to a watchlist."""
        
        try:
            # Check if watchlist exists
            result = await self.session.execute(
                select(Watchlist).where(Watchlist.id == watchlist_id)
            )
            watchlist = result.scalar_one_or_none()
            
            if not watchlist:
                raise WatchlistNotFoundError(f"Watchlist with ID {watchlist_id} not found")
            
            # Check if currencies exist
            await self._get_currency(base_currency)
            await self._get_currency(target_currency)
            
            # Check if item already exists
            result = await self.session.execute(
                select(WatchlistItem).where(
                    WatchlistItem.watchlist_id == watchlist_id,
                    WatchlistItem.base_currency == base_currency.upper(),
                    WatchlistItem.target_currency == target_currency.upper()
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                raise DuplicateWatchlistItemError(
                    f"Currency pair {base_currency}/{target_currency} already exists in watchlist"
                )
            
            # Get max position
            result = await self.session.execute(
                select(WatchlistItem)
                .where(WatchlistItem.watchlist_id == watchlist_id)
                .order_by(WatchlistItem.position.desc())
                .limit(1)
            )
            last_item = result.scalar_one_or_none()
            position = (last_item.position + 1) if last_item else 0
            
            item = WatchlistItem(
                watchlist_id=watchlist_id,
                base_currency=base_currency.upper(),
                target_currency=target_currency.upper(),
                currency_type=currency_type,
                position=position
            )
            self.session.add(item)
            await self.session.commit()
            await self.session.refresh(item)
            
            return WatchlistItemResponse(
                id=item.id,
                watchlist_id=item.watchlist_id,
                base_currency=item.base_currency,
                target_currency=item.target_currency,
                type=item.currency_type,
                added_at=item.added_at
            )
            
        except (WatchlistNotFoundError, DuplicateWatchlistItemError, CurrencyNotFoundError):
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in add_item: {e}")
            raise
    
    async def remove_item(self, watchlist_id: int, item_id: int) -> WatchlistItemDeleteResponse:
        """Remove a currency pair from a watchlist."""
        
        try:
            result = await self.session.execute(
                select(WatchlistItem).where(
                    WatchlistItem.id == item_id,
                    WatchlistItem.watchlist_id == watchlist_id
                )
            )
            item = result.scalar_one_or_none()
            
            if not item:
                raise WatchlistItemNotFoundError(
                    f"Watchlist item with ID {item_id} not found in watchlist {watchlist_id}"
                )
            
            await self.session.delete(item)
            await self.session.commit()
            
            return WatchlistItemDeleteResponse(
                message="Item successfully removed from watchlist"
            )
            
        except WatchlistItemNotFoundError:
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in remove_item: {e}")
            raise
    
    async def _get_currency(self, code: str) -> Currency:
        """Get currency by code."""
        
        result = await self.session.execute(
            select(Currency).where(Currency.code == code.upper())
        )
        currency = result.scalar_one_or_none()
        
        if not currency:
            raise CurrencyNotFoundError(f"Currency '{code}' not found")
        
        return currency
