import logging
from typing import List, Optional
from supabase import create_client, Client
from models.config import settings
from models.schemas import User, Listing, SearchResult

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        print("[DB] Initialized Supabase Client")

    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Fetches user information."""
        try:
            print(f"[DB] Fetching user {telegram_id}")
            response = self.supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
            if response.data:
                print(f"[DB] User {telegram_id} found: {response.data[0].get('username')}")
                return User(**response.data[0])
            print(f"[DB] User {telegram_id} not found")
            return None
        except Exception as e:
            print(f"[DB ERROR] get_user: {e}")
            logger.error(f"Error fetching user {telegram_id}: {e}")
            return None

    async def upsert_user(self, user: User) -> None:
        """Saves or updates user information."""
        try:
            print(f"[DB] Upserting user {user.telegram_id}")
            data = user.model_dump(exclude_none=True)
            self.supabase.table("users").upsert(data).execute()
            print(f"[DB] User {user.telegram_id} upserted successfully")
        except Exception as e:
            print(f"[DB ERROR] upsert_user: {e}")
            logger.error(f"Error upserting user {user.telegram_id}: {e}")

    async def create_listing(self, listing: Listing) -> None:
        """Creates a new skill listing with its embedding."""
        try:
            print(f"[DB] Creating listing for user {listing.telegram_id}: '{listing.skill_text}'")
            self.supabase.table("listings").insert(listing.model_dump(exclude_none=True)).execute()
            print(f"[DB] Listing created successfully")
        except Exception as e:
            print(f"[DB ERROR] create_listing: {e}")
            logger.error(f"Error creating listing for user {listing.telegram_id}: {e}")
            raise

    async def get_user_listings(self, telegram_id: int) -> List[Listing]:
        """Fetches all listings for a specific user, excluding the large embedding column."""
        try:
            print(f"[DB] Fetching listings for user {telegram_id}")
            response = self.supabase.table("listings") \
                .select("id, telegram_id, skill_text, description, fee_text, college, created_at") \
                .eq("telegram_id", telegram_id) \
                .order("created_at") \
                .execute()
            
            print(f"[DB] Found {len(response.data)} listings")
            listings = []
            for item in response.data:
                try:
                    if item.get("fee_text") is None:
                        item["fee_text"] = "Not set"
                    listings.append(Listing(**item))
                except Exception as e:
                    print(f"[DB ERROR] Parsing listing item: {e}")
            return listings
        except Exception as e:
            print(f"[DB ERROR] get_user_listings: {e}")
            return []

    async def delete_listing(self, listing_id: str, telegram_id: int) -> bool:
        """Deletes a listing if it belongs to the user."""
        try:
            print(f"[DB] Deleting listing {listing_id} for user {telegram_id}")
            response = self.supabase.table("listings").delete().eq("id", listing_id).eq("telegram_id", telegram_id).execute()
            success = len(response.data) > 0
            print(f"[DB] Delete success: {success}")
            return success
        except Exception as e:
            print(f"[DB ERROR] delete_listing: {e}")
            return False

    async def keyword_match_listings(self, query_text: str, college: str, count: int = 5) -> List[SearchResult]:
        """Lightning Trigram Match - Extremely fast fuzzy search for headings."""
        try:
            print(f"[DB] Performing Lightning Trigram match for '{query_text}'")
            response = self.supabase.rpc("keyword_search_trigram", {
                "query_text": query_text,
                "filter_college": college,
                "match_threshold": 0.3, # Catching 'math' vs 'maths'
                "match_count": count
            }).execute()
            
            results = [SearchResult(**item) for item in (response.data or [])]
            print(f"[DB] Trigram match found {len(results)} results")
            return results
        except Exception as e:
            print(f"[DB ERROR] keyword_match_trigram: {e}")
            return []

    async def match_listings(self, query_text: str, query_embedding: List[float], college: str, threshold: float = 0.35, count: int = 5) -> List[SearchResult]:
        """Performs a semantic vector match."""
        try:
            print(f"[DB] Performing Semantic Vector match (threshold={threshold})")
            rpc_response = self.supabase.rpc("match_listings", {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": count,
                "filter_college": college
            }).execute()
            
            results = [SearchResult(**item) for item in (rpc_response.data or [])]
            print(f"[DB] Semantic match found {len(results)} results")
            return results
        except Exception as e:
            print(f"[DB ERROR] semantic_match: {e}")
            return []

    async def get_all_college_listings(self, college: str, limit: int = 100) -> List[SearchResult]:
        """Fetches all listings for a specific college with provider names."""
        try:
            print(f"[DB] Fetching all skills for {college}")
            response = self.supabase.table("listings") \
                .select("id, skill_text, description, fee_text, users(username, display_name)") \
                .eq("college", college) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            results = []
            for item in (response.data or []):
                user_info = item.get("users", {})
                results.append(SearchResult(
                    id=item["id"],
                    username=user_info.get("username"),
                    display_name=user_info.get("display_name"),
                    skill_text=item["skill_text"],
                    description=item.get("description"),
                    fee_text=item.get("fee_text", "Not set"),
                    similarity=1.0
                ))
            
            print(f"[DB] Found {len(results)} total skills in {college}")
            return results
        except Exception as e:
            print(f"[DB ERROR] get_all_college_listings: {e}")
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
