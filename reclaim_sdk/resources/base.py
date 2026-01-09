from pydantic import BaseModel, Field, PrivateAttr, ConfigDict
from datetime import datetime
from typing import ClassVar, Dict, List, Optional, Type, TypeVar, Any
from reclaim_sdk.client import ReclaimClient

T = TypeVar("T", bound="BaseResource")


class BaseResource(BaseModel):
    """
    Base class for all Reclaim API resources.

    Provides CRUD operations and client management using Pydantic v2 best practices.
    """

    model_config = ConfigDict(
        populate_by_name=True,  # Allow both alias and field name
        extra="ignore",  # Ignore unknown fields from API (forward compatibility)
        validate_assignment=True,  # Re-validate on field assignment
    )

    id: Optional[int] = Field(None, description="Unique identifier of the resource")
    created: Optional[datetime] = Field(None, description="Creation timestamp")
    updated: Optional[datetime] = Field(None, description="Last update timestamp")

    ENDPOINT: ClassVar[str] = ""
    _client: ReclaimClient = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        """Initialize client after model validation."""
        # Use singleton client by default
        self._client = ReclaimClient()

    @classmethod
    def from_api_data(cls: Type[T], data: Dict, client: Optional[ReclaimClient] = None) -> T:
        """
        Create instance from API response data.

        Args:
            data: API response dictionary
            client: Optional client to bind to the instance

        Returns:
            New instance of the resource
        """
        instance = cls.model_validate(data)
        if client is not None:
            instance._client = client
        return instance

    def to_api_data(self, exclude_unset: bool = True) -> Dict:
        """
        Convert to API request data.

        Args:
            exclude_unset: If True, exclude fields that weren't explicitly set.
                          This prevents overwriting server defaults with null.

        Returns:
            Dictionary suitable for API request
        """
        return self.model_dump(
            exclude_unset=exclude_unset,
            by_alias=True,
            exclude_none=True,  # Don't send null values
        )

    def _update_from_response(self, data: Dict) -> None:
        """
        Update this instance from API response data.

        Uses Pydantic's proper update mechanism to maintain validation.
        """
        # Validate new data and update fields properly
        updated = self.model_validate(data)
        # Copy validated fields to self (use class to avoid deprecation warning)
        for field_name in self.__class__.model_fields:
            setattr(self, field_name, getattr(updated, field_name))

    @classmethod
    def get(cls: Type[T], id: int, client: Optional[ReclaimClient] = None) -> T:
        """
        Fetch a resource by ID.

        Args:
            id: Resource ID
            client: Optional client instance

        Returns:
            Resource instance
        """
        if client is None:
            client = ReclaimClient()
        data = client.get(f"{cls.ENDPOINT}/{id}")
        return cls.from_api_data(data, client=client)

    def refresh(self) -> None:
        """Refresh this resource from the server."""
        if self.id is None:
            raise ValueError("Cannot refresh a resource without an ID")
        data = self._client.get(f"{self.ENDPOINT}/{self.id}")
        self._update_from_response(data)

    def save(self) -> None:
        """Save this resource to the server (create or update)."""
        data = self.to_api_data()
        if self.id is not None:
            response = self._client.patch(f"{self.ENDPOINT}/{self.id}", json=data)
        else:
            response = self._client.post(self.ENDPOINT, json=data)
        self._update_from_response(response)

    def delete(self) -> None:
        """Delete this resource from the server."""
        if self.id is None:
            raise ValueError("Cannot delete a resource without an ID")
        self._client.delete(f"{self.ENDPOINT}/{self.id}")

    @classmethod
    def list(cls: Type[T], client: Optional[ReclaimClient] = None, **params) -> List[T]:
        """
        List all resources of this type.

        Args:
            client: Optional client instance
            **params: Query parameters to pass to the API

        Returns:
            List of resource instances
        """
        if client is None:
            client = ReclaimClient()
        data = client.get(cls.ENDPOINT, params=params)
        return [cls.from_api_data(item, client=client) for item in data]
