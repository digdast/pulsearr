import re
from typing import Optional, Dict, Any, Tuple
from ..models import ParsedRelease

class ReleaseParser:
    def __init__(self):
        # Compiled regex patterns for speed
        self._re_season_episode = re.compile(
            r'(?:[sS](?P<season>\d{1,2})[eE](?P<episode>\d{1,3})(?:-[eE]?(?P<episode_end>\d{1,3}))?)|'
            r'(?:(?P<season_x>\d{1,2})[xX](?P<episode_x>\d{1,3}))|'
            r'(?:[sS](?P<season_only>\d{1,2})\b(?!\s*[eE]\d+))|'
            r'(?:Season\s*(?P<season_word>\d{1,2})\b)',
            re.IGNORECASE
        )
        
        self._re_resolution = re.compile(
            r'\b(?P<res>2160p|4k|uhd|1080p|1080i|720p|576p|480p)\b',
            re.IGNORECASE
        )
        
        self._re_source = re.compile(
            r'\b(?P<src>remux|bluray|blu-ray|bdrip|brrip|web-dl|webdl|web-rip|webrip|web|hdtv|pdtv|dvdrip|dvd)\b',
            re.IGNORECASE
        )
        
        self._re_codec = re.compile(
            r'\b(?P<codec>x265|h\.?265|hevc|x264|h\.?264|avc|av1|xvid|divx)\b',
            re.IGNORECASE
        )
        
        self._re_hdr = re.compile(
            r'\b(?P<hdr>dv|dovi|dolby\s*vision|hdr10\+|hdr10|hdr)\b',
            re.IGNORECASE
        )
        
        self._re_audio = re.compile(
            r'\b(?P<audio>atmos|truehd|dts-hd\s*ma|dts-hd|dts|eac3|ddp\s*5\.1|dd\+?|ac3|aac(?:\s*2\.0)?|flac|mp3)\b',
            re.IGNORECASE
        )
        
        self._re_flags = re.compile(
            r'\b(?P<flag>proper|repack|real)\b',
            re.IGNORECASE
        )
        
        self._re_group = re.compile(
            r'-([a-zA-Z0-9_]+)(?:\[.*?\])?(?:\.mkv|\.mp4|\.avi)?$',
            re.IGNORECASE
        )

    def parse(self, raw_title: str) -> ParsedRelease:
        """Parses a release string into structured components."""
        clean_raw = raw_title.replace('_', '.').replace(' ', '.')
        # Normalize double dots
        clean_raw = re.sub(r'\.+', '.', clean_raw)

        # 1. Season & Episode Detection
        season = None
        episode = None
        season_pack = False
        
        match_se = self._re_season_episode.search(clean_raw)
        title_cutoff_idx = len(clean_raw)
        
        if match_se:
            title_cutoff_idx = match_se.start()
            gd = match_se.groupdict()
            if gd.get("season"):
                season = int(gd["season"])
                episode = int(gd["episode"])
            elif gd.get("season_x"):
                season = int(gd["season_x"])
                episode = int(gd["episode_x"])
            elif gd.get("season_only"):
                season = int(gd["season_only"])
                season_pack = True
            elif gd.get("season_word"):
                season = int(gd["season_word"])
                season_pack = True

        # Extract Series Name
        raw_series_name = clean_raw[:title_cutoff_idx].strip('.')
        # Clean out common prefixes/bracket garbage
        raw_series_name = re.sub(r'^\[.*?\]', '', raw_series_name)
        # Remove trailing year from series title if present e.g. "Severance.2022" -> "Severance"
        year_match = re.search(r'\.(19\d\d|20\d\d)$', raw_series_name)
        if year_match:
            raw_series_name = raw_series_name[:year_match.start()]
            
        clean_title = raw_series_name.replace('.', ' ').strip()
        
        # 2. Resolution
        res = "Unknown"
        match_res = self._re_resolution.search(clean_raw)
        if match_res:
            r = match_res.group("res").lower()
            if r in ("4k", "uhd"):
                res = "2160p"
            else:
                res = r

        # 3. Source
        source = "Unknown"
        match_src = self._re_source.search(clean_raw)
        if match_src:
            s = match_src.group("src").lower()
            if "remux" in s:
                source = "Remux"
            elif "bluray" in s or "blu-ray" in s or "bdrip" in s or "brrip" in s:
                source = "BluRay"
            elif "web-dl" in s or "webdl" in s:
                source = "WEB-DL"
            elif "webrip" in s or "web-rip" in s or s == "web":
                source = "WEBRip"
            elif "hdtv" in s or "pdtv" in s:
                source = "HDTV"
            elif "dvd" in s:
                source = "DVD"

        # 4. Codec
        codec = "Unknown"
        match_codec = self._re_codec.search(clean_raw)
        if match_codec:
            c = match_codec.group("codec").lower()
            if c in ("x265", "h265", "hevc"):
                codec = "HEVC"
            elif c in ("x264", "h264", "avc"):
                codec = "x264"
            elif c == "av1":
                codec = "AV1"
            elif c in ("xvid", "divx"):
                codec = "XviD"

        # 5. HDR
        hdr = "SDR"
        match_hdr = self._re_hdr.search(clean_raw)
        if match_hdr:
            h = match_hdr.group("hdr").lower()
            if "dv" in h or "dovi" in h or "dolby" in h:
                hdr = "Dolby Vision"
            elif "hdr10+" in h:
                hdr = "HDR10+"
            elif "hdr" in h:
                hdr = "HDR10"

        # 6. Audio
        audio = "Unknown"
        match_audio = self._re_audio.search(clean_raw)
        if match_audio:
            a = match_audio.group("audio").upper()
            audio = a

        # 7. Flags (Proper / Repack)
        proper = False
        repack = False
        match_flags = self._re_flags.search(clean_raw)
        if match_flags:
            f = match_flags.group("flag").lower()
            if "proper" in f:
                proper = True
            if "repack" in f or "real" in f:
                repack = True

        # 8. Release Group
        release_group = "Unknown"
        match_grp = self._re_group.search(raw_title)
        if match_grp:
            release_group = match_grp.group(1).strip()

        # Quality Tag synthesis
        quality_tag = f"{source}-{res}" if source != "Unknown" and res != "Unknown" else (res if res != "Unknown" else source)
        if hdr != "SDR":
            quality_tag += f" {hdr}"

        # Base scoring algorithm
        score = 0
        if res == "2160p":
            score += 100
        elif res == "1080p":
            score += 80
        elif res == "720p":
            score += 60
        elif res == "480p":
            score += 30

        if source == "Remux":
            score += 40
        elif source == "BluRay":
            score += 35
        elif source == "WEB-DL":
            score += 30
        elif source == "WEBRip":
            score += 25
        elif source == "HDTV":
            score += 15

        if codec == "HEVC":
            score += 10
        elif codec == "AV1":
            score += 12

        if proper or repack:
            score += 5

        return ParsedRelease(
            title=raw_title,
            clean_title=clean_title,
            season=season,
            episode=episode,
            season_pack=season_pack,
            resolution=res,
            source=source,
            codec=codec,
            audio=audio,
            hdr=hdr,
            release_group=release_group,
            proper=proper,
            repack=repack,
            quality_tag=quality_tag,
            score=score
        )

release_parser = ReleaseParser()
