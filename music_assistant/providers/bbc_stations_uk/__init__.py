"""
DEMO/TEMPLATE Music Provider for Music Assistant.

This is an empty music provider with no actual implementation.
Its meant to get started developing a new music provider for Music Assistant.

Use it as a reference to discover what methods exists and what they should return.
Also it is good to look at existing music providers to get a better understanding,
due to the fact that providers may be flexible and support different features.

If you are relying on a third-party library to interact with the music source,
you can then reference your library in the manifest in the requirements section,
which is a list of (versioned!) python modules (pip syntax) that should be installed
when the provider is selected by the user.

Please keep in mind that Music Assistant is a fully async application and all
methods should be implemented as async methods. If you are not familiar with
async programming in Python, we recommend you to read up on it first.
If you are using a third-party library that is not async, you can need to use the several
helper methods such as asyncio.to_thread or the create_task in the mass object to wrap
the calls to the library in a thread.

To add a new provider to Music Assistant, you need to create a new folder
in the providers folder with the name of your provider (e.g. 'my_music_provider').
In that folder you should create (at least) a __init__.py file and a manifest.json file.

Optional is an icon.svg file that will be used as the icon for the provider in the UI,
but we also support that you specify a material design icon in the manifest.json file.

"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING

from music_assistant_models.enums import ContentType, MediaType, ProviderFeature, StreamType
from music_assistant_models.media_items import (
    Album,
    Artist,
    AudioFormat,
    BrowseFolder,
    ItemMapping,
    MediaItemType,
    Playlist,
    ProviderMapping,
    Radio,
    RecommendationFolder,
    SearchResults,
    Track,
)
from music_assistant_models.streamdetails import StreamDetails

from music_assistant.models.music_provider import MusicProvider

SUPPORTED_FEATURES = {
    ProviderFeature.SEARCH,
    ProviderFeature.BROWSE,
    # RadioBrowser doesn't support a library feature at all
    # but MA users like to favorite their radio stations and
    # have that included in backups so we store it in the config.
    ProviderFeature.LIBRARY_RADIOS,
    ProviderFeature.LIBRARY_RADIOS_EDIT,
}

CONF_STORED_RADIOS = "stored_uk_bbc_radios"


# --- Config ------------------------------------------------------------------

# Keep this minimal: UK region only; change to "ww" if you want worldwide.
BBC_REGION = "uk"

# Default bitrate preference (can be 96000 or 320000).
DEFAULT_BITRATE = 320000

# Optional: icon paths (replace with your own assets if preferred).
STATION_ICONS_BASE_URL = (
    "https://raw.githubusercontent.com/music-assistant/music-assistant.io/main/docs/assets/icons"
)

# Stations: (human name, a.files slug, .isml filename, icon filename)
STATIONS: dict[str, dict[str, str]] = {
    "bbc_radio_1": {
        "name": "BBC Radio 1",
        "slug": "bbc_radio_one",
        "isml": "bbc_radio_one.isml",
        "icon": "bbc1.png",
    },
    "bbc_radio_2": {
        "name": "BBC Radio 2",
        "slug": "bbc_radio_two",
        "isml": "bbc_radio_two.isml",
        "icon": "bbc2.png",
    },
    "bbc_radio_3": {
        "name": "BBC Radio 3",
        "slug": "bbc_radio_three",
        "isml": "bbc_radio_three.isml",
        "icon": "bbc3.png",
    },
    "bbc_radio_4": {
        "name": "BBC Radio 4 (FM)",
        "slug": "bbc_radio_fourfm",
        "isml": "bbc_radio_fourfm.isml",
        "icon": "bbc4.png",
    },
    "bbc_radio_5live": {
        "name": "BBC Radio 5 Live",
        "slug": "bbc_radio_five_live",
        "isml": "bbc_radio_five_live.isml",
        "icon": "bbc5.png",
    },
    "bbc_6music": {
        "name": "BBC Radio 6 Music",
        "slug": "bbc_6music",
        "isml": "bbc_6music.isml",
        "icon": "bbc6.png",
    },
}

if TYPE_CHECKING:
    from music_assistant_models.config_entries import ConfigEntry, ConfigValueType, ProviderConfig
    from music_assistant_models.provider import ProviderManifest

    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType



async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    # setup is called when the user wants to setup a new provider instance.
    # you are free to do any preflight checks here and but you must return
    #  an instance of the provider.
    return UkBbcRadioStationsProvider(mass, manifest, config)


async def get_config_entries(
    mass: MusicAssistant,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    """
    Return Config entries to setup this provider.
    instance_id: id of an existing provider instance (None if new instance setup).
    action: [optional] action key called from config entries UI.
    values: the (intermediate) raw values for config entries sent with the action.
    """
    # ruff: noqa: ARG001 D205
    return (
        ConfigEntry(
            # RadioBrowser doesn't support a library feature at all
            # but MA users like to favorite their radio stations and
            # have that included in backups so we store it in the config.
            key=CONF_STORED_RADIOS,
            type=ConfigEntryType.STRING,
            multi_value=True,
            label=CONF_STORED_RADIOS,
            default_value=[],
            required=False,
            hidden=True,
        ),
    )

class UkBbcRadioStationsProvider(MusicProvider):
    """
    UK BBC Radio Station  Music provider.

    Music provider for UK streams of BBC Radio Stations.


    Just like with any other subclass, make sure that if you override
    any of the default methods (such as __init__), you call the super() method.
    In most cases its not needed to override any of the builtin methods and you only
    implement the abc methods with your actual implementation.
    """

    @property
    def supported_features(self) -> set[ProviderFeature]:
        """Return the features supported by this Provider."""
        return SUPPORTED_FEATURES

    async def loaded_in_mass(self) -> None:
        """Call after the provider has been loaded."""
        # OPTIONAL
        # this is an optional method that you can implement if
        # relevant or leave out completely if not needed.
        # In most cases this can be omitted for music providers.

    async def unload(self, is_removed: bool = False) -> None:
        """
        Handle unload/close of the provider.

        Called when provider is deregistered (e.g. MA exiting or config reloading).
        is_removed will be set to True when the provider is removed from the configuration.
        """
        # OPTIONAL
        # This is an optional method that you can implement if
        # relevant or leave out completely if not needed.
        # It will be called when the provider is unloaded from Music Assistant.
        # for example to disconnect from a service or clean up resources.

    @property
    def is_streaming_provider(self) -> bool:
        """
        Return True if the provider is a streaming provider.

        This literally means that the catalog is not the same as the library contents.
        For local based providers (files, plex), the catalog is the same as the library content.
        It also means that data is if this provider is NOT a streaming provider,
        data cross instances is unique, the catalog and library differs per instance.

        Setting this to True will only query one instance of the provider for search and lookups.
        Setting this to False will query all instances of this provider for search and lookups.
        """
        # For streaming providers return True here but for local file based providers return False.
        return True

    async def search(  # type: ignore[empty-body]
        self,
        search_query: str,
        media_types: list[MediaType],
        limit: int = 5,
    ) -> SearchResults:
        """Perform search on musicprovider.

        :param search_query: Search query.
        :param media_types: A list of media_types to include.
        :param limit: Number of items to return in the search (per type).
        """
        # OPTIONAL
        # Will only be called if you reported the SEARCH feature in the supported_features.
        # It allows searching your provider for media items.
        # See the model for SearchResults for more information on what to return, but
        # in general you should return a list of MediaItems for each media type.


    # --- Library / Browse ----------------------------------------------------

    async def get_library_radios(self) -> AsyncGenerator[Radio, None]:
        for prov_id in STATIONS:
            yield self._parse_radio(prov_id)

    async def get_radio(self, prov_radio_id: str) -> Radio:
        if prov_radio_id not in STATIONS:
            raise MediaNotFoundError("Station not found")
        return self._parse_radio(prov_radio_id)

    async def browse(self, path: str) -> Sequence[MediaItemType | ItemMapping | BrowseFolder]:
        return [self._parse_radio(prov_id) for prov_id in STATIONS]


    # -- Library Add/Remove functions

    async def library_add(self, item: MediaItemType) -> bool:
        """Add item to provider's library. Return true on success."""
        stored_radios = self.config.get_value(CONF_STORED_RADIOS)
        if TYPE_CHECKING:
            stored_radios = cast("list[str]", stored_radios)
        if item.item_id in stored_radios:
            return False
        self.logger.debug("Adding radio %s to stored radios", item.item_id)
        stored_radios = [*stored_radios, item.item_id]
        self.update_config_value(CONF_STORED_RADIOS, stored_radios)
        return True

    async def library_remove(self, prov_item_id: str, media_type: MediaType) -> bool:
        """Remove item from provider's library. Return true on success."""
        stored_radios = self.config.get_value(CONF_STORED_RADIOS)
        if TYPE_CHECKING:
            stored_radios = cast("list[str]", stored_radios)
        if prov_item_id not in stored_radios:
            return False
        self.logger.debug("Removing radio %s from stored radios", prov_item_id)
        stored_radios = [x for x in stored_radios if x != prov_item_id]
        self.update_config_value(CONF_STORED_RADIOS, stored_radios)
        return True

    # --- Playback ------------------------------------------------------------

    async def get_stream_details(self, item_id: str, media_type: MediaType) -> StreamDetails:
        if media_type != MediaType.RADIO:
            raise UnplayableMediaError(f"Unsupported media type: {media_type}")
        if item_id not in STATIONS:
            raise MediaNotFoundError(f"Unknown station: {item_id}")

        station = STATIONS[item_id]
        # 1) Discover current Akamai pool via a.files manifest
        variant_url = await self._discover_variant_url(station["slug"])
        # 2) Convert to stable (non-token) UK no-rewind URL at preferred bitrate
        stable_url = self._to_static_url(variant_url, station["isml"], self.preferred_bitrate)

        return StreamDetails(
            item_id=item_id,
            provider=self.lookup_key,
            audio_format=AudioFormat(
                content_type=ContentType.AAC,  # BBC HLS = AAC-LC
                channels=2,
            ),
            media_type=MediaType.RADIO,
            stream_type=StreamType.HLS,
            path=stable_url,
            allow_seek=False,
            can_seek=False,
            duration=0,
        )

    async def on_streamed(self, streamdetails: StreamDetails) -> None:
        # Nothing to clean up in this minimal provider.
        self.logger.debug(
            f"BBC station {streamdetails.item_id} streamed for {streamdetails.seconds_streamed} s"
        )

    # --- Helpers -------------------------------------------------------------

    def _parse_radio(self, prov_id: str) -> Radio:
        st = STATIONS[prov_id]
        radio = Radio(
            provider=self.lookup_key,
            item_id=prov_id,
            name=st["name"],
            provider_mappings={
                ProviderMapping(
                    provider_domain=self.domain,
                    provider_instance=self.instance_id,
                    item_id=prov_id,
                    available=True,
                )
            },
        )
        # Optional icon (replace with your own assets as needed)
        icon = st.get("icon")
        if icon:
            radio.metadata.add_image(
                MediaItemImage(
                    provider=self.lookup_key,
                    type=ImageType.THUMB,
                    path=f"{STATION_ICONS_BASE_URL}/{icon}",
                    remotely_accessible=True,
                )
            )
        return radio

    async def _discover_variant_url(self, slug: str) -> str:
        """Fetch the BBC 'a.files' manifest and return any variant .m3u8 URL for this slug.

        We use the provider's shared aiohttp session.
        """
        manifest_url = A_FILES_TPL.format(slug=slug)
        timeout = aiohttp.ClientTimeout(total=10)

        async with self.mass.http_session.get(manifest_url, timeout=timeout, allow_redirects=True) as r:
            r.raise_for_status()
            text = await r.text()
            # If the final URL itself already points into Akamai with the station path, use it.
            if r.url and slug in str(r.url):
                return str(r.url)

        # Fallback: fetch again and parse body lines (kept separate to avoid reusing closed r)
        async with self.mass.http_session.get(manifest_url, timeout=timeout) as r2:
            r2.raise_for_status()
            body = await r2.text()
            for line in (ln.strip() for ln in body.splitlines()):
                if line and not line.startswith("#") and line.endswith(".m3u8") and slug in line:
                    return line
        raise UnplayableMediaError(f"Could not locate a variant URL for {slug}")

    def _to_static_url(self, any_m3u8_url: str, isml: str, bitrate: int) -> str:
        """Trim to the .isml directory and append a non-rewind variant at the chosen bitrate."""
        # We avoid urlparse joins to keep it robust across Akamai variants.
        # Example in → https://as-hls-uk-live.akamaized.net/pool_x/live/uk/<slug>/<isml>/playlist.m3u8?... → out: .../<isml>/<slug>-audio=<bitrate>.norewind.m3u8
        # Extract scheme://netloc and path:
        from urllib.parse import urlparse

        p = urlparse(any_m3u8_url)
        parts = [seg for seg in p.path.split("/") if seg]
        try:
            idx = parts.index(isml)
        except ValueError as exc:
            raise UnplayableMediaError(f"Expected {isml} in path: {any_m3u8_url}") from exc

        base = "/" + "/".join(parts[: idx + 1])
        slug_no_ext = isml.replace(".isml", "")
        return f"{p.scheme}://{p.netloc}{base}/{slug_no_ext}-audio={bitrate}.norewind.m3u8"
