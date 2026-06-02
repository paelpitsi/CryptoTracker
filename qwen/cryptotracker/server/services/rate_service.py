"""Rate service for handling currency rates and conversions."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from cryptotracker.server.models.currency import Currency
from cryptotracker.server.models.query_history import QueryHistory, QueryHistoryItem
from cryptotracker.server.external.frankfurter import FrankfurterClient
from cryptotracker.server.external.coingecko import CoinGeckoClient
from cryptotracker.server.schemas.rates import RateItem, RatesResponse, ConvertResponse
from cryptotracker.common.exceptions import CurrencyNotFoundError, ExternalAPIError
from cryptotracker.common.logger import logger


class RateService:
    """Service for managing currency rates and conversions."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.frankfurter = FrankfurterClient()
        self.coingecko = CoinGeckoClient()
    
    async def get_rates(
        self,
        base: str,
        targets: list[str],
        currency_type: str = "all"
    ) -> RatesResponse:
        """Get exchange rates for multiple target currencies."""
        
        start_time = datetime.utcnow()
        rates = []
        error_message = None
        status = "success"
        
        try:
            # Check if base is crypto
            base_currency = await self._get_currency(base)
            base_is_crypto = base_currency.type == "crypto"
            
            # Separate fiat and crypto targets
            fiat_targets = []
            crypto_targets = []
            
            for target in targets:
                currency = await self._get_currency(target)
                if currency.type == "fiat":
                    fiat_targets.append(target)
                else:
                    crypto_targets.append(target)
            
            # If base is crypto, use CoinGecko for all targets
            if base_is_crypto and currency_type in ["crypto", "all"]:
                try:
                    # Get coingecko ID for base crypto
                    if not base_currency.coingecko_id:
                        raise CurrencyNotFoundError(f"CoinGecko ID not found for {base}")
                    
                    # Determine vs_currencies for CoinGecko
                    vs_currencies = []
                    for target in targets:
                        target_currency = await self._get_currency(target)
                        if target_currency.type == "fiat":
                            vs_currencies.append(target.lower())
                        else:
                            # For crypto-to-crypto, we need to get both in USD and calculate
                            vs_currencies.append("usd")
                    
                    vs_currencies = list(set(vs_currencies))
                    
                    # Get base crypto price
                    base_prices = await self.coingecko.get_simple_price(
                        ids=[base_currency.coingecko_id],
                        vs_currencies=vs_currencies,
                        include_24h_change=True
                    )
                    
                    if base_currency.coingecko_id not in base_prices:
                        raise ExternalAPIError(f"Failed to get price for {base}")
                    
                    base_price_data = base_prices[base_currency.coingecko_id]
                    
                    # Process each target
                    for target in targets:
                        target_currency = await self._get_currency(target)
                        
                        if target_currency.type == "fiat":
                            # Direct conversion from crypto to fiat
                            rate = base_price_data.get(target.lower(), 0)
                            change = base_price_data.get(f"{target.lower()}_24h_change")
                            
                            rates.append(RateItem(
                                target=target,
                                rate=Decimal(str(rate)),
                                type="crypto",
                                change_24h=Decimal(str(change)) if change else None
                            ))
                        else:
                            # Crypto-to-crypto: get both in USD and calculate ratio
                            if not target_currency.coingecko_id:
                                continue
                            
                            target_prices = await self.coingecko.get_simple_price(
                                ids=[target_currency.coingecko_id],
                                vs_currencies=["usd"],
                                include_24h_change=True
                            )
                            
                            if target_currency.coingecko_id in target_prices:
                                base_usd = base_price_data.get("usd", 0)
                                target_usd = target_prices[target_currency.coingecko_id].get("usd", 0)
                                
                                if target_usd > 0:
                                    rate = base_usd / target_usd
                                    change = base_price_data.get("usd_24h_change")
                                    
                                    rates.append(RateItem(
                                        target=target,
                                        rate=Decimal(str(rate)),
                                        type="crypto",
                                        change_24h=Decimal(str(change)) if change else None
                                    ))
                
                except Exception as e:
                    logger.error(f"Failed to get crypto rates: {e}")
                    if currency_type == "crypto":
                        raise
                    status = "partial"
                    error_message = f"Failed to get crypto rates: {e}"
            
            # If base is fiat, use normal logic
            else:
                # Get fiat rates from Frankfurter
                if fiat_targets and currency_type in ["fiat", "all"]:
                    try:
                        fiat_rates = await self.frankfurter.get_latest_rates(base, fiat_targets)
                        for target in fiat_targets:
                            if target in fiat_rates:
                                rates.append(RateItem(
                                    target=target,
                                    rate=Decimal(str(fiat_rates[target])),
                                    type="fiat",
                                    change_24h=None
                                ))
                    except Exception as e:
                        logger.error(f"Failed to get fiat rates: {e}")
                        if currency_type == "fiat":
                            raise
                        status = "partial"
                        error_message = f"Failed to get fiat rates: {e}"
                
                # Get crypto rates from CoinGecko
                if crypto_targets and currency_type in ["crypto", "all"]:
                    try:
                        # Get coingecko IDs for crypto currencies
                        crypto_ids = []
                        crypto_map = {}
                        for target in crypto_targets:
                            currency = await self._get_currency(target)
                            if currency.coingecko_id:
                                crypto_ids.append(currency.coingecko_id)
                                crypto_map[currency.coingecko_id] = target
                        
                        if crypto_ids:
                            # Determine base currency for CoinGecko
                            vs_currency = base.lower()
                            
                            crypto_prices = await self.coingecko.get_simple_price(
                                ids=crypto_ids,
                                vs_currencies=[vs_currency],
                                include_24h_change=True
                            )
                            
                            for coin_id, target in crypto_map.items():
                                if coin_id in crypto_prices:
                                    price_data = crypto_prices[coin_id]
                                    rate = price_data.get(vs_currency, 0)
                                    change = price_data.get(f"{vs_currency}_24h_change")
                                    
                                    rates.append(RateItem(
                                        target=target,
                                        rate=Decimal(str(rate)),
                                        type="crypto",
                                        change_24h=Decimal(str(change)) if change else None
                                    ))
                    except Exception as e:
                        logger.error(f"Failed to get crypto rates: {e}")
                        if currency_type == "crypto":
                            raise
                        status = "partial"
                        if error_message:
                            error_message += f"; Failed to get crypto rates: {e}"
                        else:
                            error_message = f"Failed to get crypto rates: {e}"
            
            # Save to history
            end_time = datetime.utcnow()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            query_history = QueryHistory(
                command_type="rate",
                status=status,
                error_message=error_message,
                response_time_ms=response_time_ms
            )
            self.session.add(query_history)
            await self.session.flush()
            
            # Save rate items
            for rate_item in rates:
                history_item = QueryHistoryItem(
                    query_history_id=query_history.id,
                    base_currency=base,
                    target_currency=rate_item.target,
                    rate=rate_item.rate,
                    amount=Decimal("1.0"),
                    currency_type=rate_item.type,
                    change_24h=rate_item.change_24h
                )
                self.session.add(history_item)
            
            await self.session.commit()
            
            return RatesResponse(
                base=base,
                timestamp=datetime.utcnow(),
                rates=rates,
                query_id=query_history.id
            )
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in get_rates: {e}")
            raise
    
    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        currency_type: str = "auto"
    ) -> ConvertResponse:
        """Convert amount from one currency to another."""
        
        start_time = datetime.utcnow()
        
        try:
            # Determine currency type if auto
            if currency_type == "auto":
                from_curr = await self._get_currency(from_currency)
                to_curr = await self._get_currency(to_currency)
                currency_type = "crypto" if from_curr.type == "crypto" or to_curr.type == "crypto" else "fiat"
            
            # Get rate
            rates_response = await self.get_rates(
                base=from_currency,
                targets=[to_currency],
                currency_type=currency_type
            )
            
            if not rates_response.rates:
                raise CurrencyNotFoundError(f"Could not get rate for {from_currency} to {to_currency}")
            
            rate_item = rates_response.rates[0]
            result = amount * rate_item.rate
            
            # Save conversion to history
            end_time = datetime.utcnow()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            query_history = QueryHistory(
                command_type="convert",
                status="success",
                response_time_ms=response_time_ms
            )
            self.session.add(query_history)
            await self.session.flush()
            
            history_item = QueryHistoryItem(
                query_history_id=query_history.id,
                base_currency=from_currency,
                target_currency=to_currency,
                rate=rate_item.rate,
                amount=amount,
                result=result,
                currency_type=rate_item.type,
                change_24h=rate_item.change_24h
            )
            self.session.add(history_item)
            await self.session.commit()
            
            return ConvertResponse(
                **{"from": from_currency, "to": to_currency},
                amount=amount,
                result=result,
                rate=rate_item.rate,
                timestamp=datetime.utcnow(),
                type=rate_item.type,
                change_24h=rate_item.change_24h,
                query_id=query_history.id
            )
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error in convert: {e}")
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
