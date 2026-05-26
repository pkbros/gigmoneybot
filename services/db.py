import logging
from typing import List, Optional
from supabase import create_client, Client
from models.config import settings
from models.schemas import User, Listing, SearchResult

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Fetches user information."""
        try:
            response = self.supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
            if response.data:
                return User(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching user {telegram_id}: {e}")
            return None

    async def upsert_user(self, user: User) -> None:
        """Saves or updates user information."""
        try:
            # Only include college if it's set, to avoid overwriting with None
            data = user.model_dump(exclude_none=True)
            self.supabase.table("users").upsert(data).execute()
        except Exception as e:
            logger.error(f"Error upserting user {user.telegram_id}: {e}")

    async def create_listing(self, listing: Listing) -> None:
        """Creates a new skill listing with its embedding."""
        try:
            self.supabase.table("listings").insert(listing.model_dump(exclude_none=True)).execute()
        except Exception as e:
            logger.error(f"Error creating listing for user {listing.telegram_id}: {e}")
            raise

    async def get_user_listings(self, telegram_id: int) -> List[Listing]:
        """Fetches all listings for a specific user, excluding the large embedding column."""
        try:
            # We explicitly list columns to EXCLUDE 'embedding' which is slow to transfer and hard to parse
            response = self.supabase.table("listings") \
                .select("id, telegram_id, skill_text, description, fee_text, college, created_at") \
                .eq("telegram_id", telegram_id) \
                .order("created_at") \
                .execute()
            
            logger.info(f"Fetched {len(response.data)} listings for user {telegram_id}")
            
            listings = []
            for item in response.data:
                try:
                    # Provide a default if fee_text is None for legacy data
                    if item.get("fee_text") is None:
                        item["fee_text"] = "Not set"
                    listings.append(Listing(**item))
                except Exception as e:
                    logger.error(f"Error parsing listing item ID {item.get('id')}: {e}")
            
            return listings
        except Exception as e:
            logger.error(f"Error fetching listings for user {telegram_id}: {e}")
            return []

    async def delete_listing(self, listing_id: str, telegram_id: int) -> bool:
        """Deletes a listing if it belongs to the user."""
        try:
            response = self.supabase.table("listings").delete().eq("id", listing_id).eq("telegram_id", telegram_id).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error deleting listing {listing_id}: {e}")
            return False

    async def match_listings(self, query_embedding: List[float], college: str, threshold: float = 0.35, count: int = 5) -> List[SearchResult]:
        """Calls the RPC function to perform semantic search with college filter."""
        try:
            response = self.supabase.rpc("match_listings", {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": count,
                "filter_college": college
            }).execute()
            
            logger.info(f"Search results for college '{college}' (threshold={threshold}): {response.data}")
            return [SearchResult(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error matching listings: {e}")
            return []

    async def get_all_college_listings(self, college: str, limit: int = 100) -> List[Listing]:
        """Fetches all listings for a specific college."""
        try:
            response = self.supabase.table("listings") \
                .select("id, telegram_id, skill_text, description, fee_text, college, created_at") \
                .eq("college", college) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            return [Listing(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching all listings for {college}: {e}")
            return []

    async def log_search(self, telegram_id: int, username: Optional[str], query: str, college: Optional[str]) -> None:
        """Logs a search query for analytics."""
        try:
            self.supabase.table("search_logs").insert({
                "telegram_id": telegram_id,
                "username": username,
                "query": query,
                "college": college
            }).execute()
        except Exception as e:
            logger.error(f"Error logging search for {telegram_id}: {e}")

    async def get_all_users(self) -> List[User]:
        """Fetches all registered users for global broadcasts."""
        try:
            response = self.supabase.table("users").select("telegram_id, username, college").execute()
            return [User(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
            return []

db_service = DatabaseService()
