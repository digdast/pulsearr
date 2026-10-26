import logging
import xml.etree.ElementTree as ET
import httpx
from typing import List, Optional, Tuple
from .base import BaseIndexer
from ..models import ReleaseCandidate
from ..parser.release_parser import release_parser

logger = logging.getLogger("pulsearr.indexers.torznab")

class TorznabIndexer(BaseIndexer):
    async def _query(self, params: dict) -> List[ReleaseCandidate]:
        query_params = {
            "apikey": self.api_key,
            "cat": self.categories,
            **params
        }
        candidates = []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(self.url, params=query_params)
                if resp.status_code != 200:
                    logger.warning(f"Torznab query failed with status {resp.status_code}: {resp.text[:100]}")
                    return []
                    
                root = ET.fromstring(resp.content)
                channel = root.find("channel")
                if channel is None:
                    return []
                    
                items = channel.findall("item")
                for item in items:
                    title_elem = item.find("title")
                    title = title_elem.text if title_elem is not None else ""
                    if not title:
                        continue
                        
                    link_elem = item.find("link")
                    download_url = link_elem.text if link_elem is not None else ""
                    
                    enclosure = item.find("enclosure")
                    size = 0
                    if enclosure is not None:
                        size = int(enclosure.attrib.get("length", 0))
                        if not download_url:
                            download_url = enclosure.attrib.get("url", "")
                            
                    guid_elem = item.find("guid")
                    guid = guid_elem.text if guid_elem is not None else title
                    
                    pub_date = item.find("pubDate")
                    publish_date = pub_date.text if pub_date is not None else None
                    
                    # Extract Torznab / Newznab attributes
                    seeders = 0
                    leechers = 0
                    protocol = "torrent"
                    
                    for child in item:
                        tag = child.tag.lower()
                        if "attr" in tag:
                            attr_name = child.attrib.get("name", "").lower()
                            attr_val = child.attrib.get("value", "0")
                            if attr_name == "seeders":
                                seeders = int(attr_val or 0)
                            elif attr_name in ("peers", "leechers"):
                                leechers = int(attr_val or 0)
                            elif attr_name == "size" and size == 0:
                                size = int(attr_val or 0)
                            elif attr_name == "protocol":
                                protocol = attr_val
                                
                    parsed = release_parser.parse(title)
                    candidate = ReleaseCandidate(
                        guid=guid,
                        indexer_id=self.id,
                        indexer_name=self.name,
                        title=title,
                        download_url=download_url,
                        protocol=protocol,
                        size=size,
                        publish_date=publish_date,
                        seeders=seeders,
                        leechers=leechers,
                        parsed=parsed
                    )
                    candidates.append(candidate)
        except Exception as e:
            logger.exception(f"Error querying Torznab indexer {self.name}: {e}")
            
        return candidates

    async def search(self, query: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[ReleaseCandidate]:
        params = {"t": "tvsearch", "q": query}
        if season is not None:
            params["season"] = str(season)
        if episode is not None:
            params["ep"] = str(episode)
        return await self._query(params)

    async def fetch_rss(self) -> List[ReleaseCandidate]:
        return await self._query({"t": "tvsearch", "limit": "100"})

    async def test_connection(self) -> Tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(self.url, params={"t": "caps", "apikey": self.api_key})
                if resp.status_code == 200:
                    return True, "Successfully connected to Torznab/Newznab indexer."
                return False, f"Server returned HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
