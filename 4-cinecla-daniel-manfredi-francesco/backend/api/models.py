from dataclasses import dataclass
from typing import Optional


@dataclass
class ImpressionRequest:
    """
    Request model for POST /api/impressions endpoint
    
    This defines what the Nicla Vision device should send.
    
    Fields:
        device_id: Unique identifier for the Nicla device 
        
        emotion: Detected emotion from the inference model
        
        frame_data: Base64-encoded camera frame (96x96 grayscale)
                    Optional
                    Format: Base64 encoded string
                    Size: ~12KB when encoded
    
    """
    device_id: str
    emotion: str
    frame_data: Optional[str] = None


@dataclass
class ImpressionResponse:

    status: str
    impression_count: int
    has_frame: bool