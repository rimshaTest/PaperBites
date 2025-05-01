# paper/license.py
"""
Module for handling paper licenses and determining if they can be publicly displayed.
"""

import logging
import re
from typing import Optional, List

logger = logging.getLogger("paperbites.license")

# List of license types that allow public display
PUBLIC_DISPLAY_LICENSES = [
    # Creative Commons licenses
    "cc-by",
    "cc by",
    "cc-by-sa",
    "cc by sa",
    "cc0",
    "cc zero",
    "creative commons",
    
    # Public domain
    "public domain",
    
    # Open access specific
    "open access",
    
    # arXiv default license
    "arxiv",
    
    # Apache and MIT licenses
    "apache",
    "mit license",
]

# List of license URLs that allow public display
PUBLIC_DISPLAY_LICENSE_URLS = [
    # Creative Commons
    "creativecommons.org/licenses/by/",
    "creativecommons.org/licenses/by-sa/",
    "creativecommons.org/publicdomain/zero/",
    "creativecommons.org/licenses/by-nc/",  # Non-commercial use is okay for educational purposes
    
    # arXiv license
    "arxiv.org/licenses/",
]

# License types that don't allow public display
RESTRICTED_LICENSES = [
    "all rights reserved",
    "copyright",
]

def is_publicly_displayable(license_info: Optional[str]) -> bool:
    """
    Check if a paper's license allows public display.
    
    Args:
        license_info: License string or URL
        
    Returns:
        bool: Whether the paper can be publicly displayed
    """
    if not license_info:
        return False
    
    license_lower = license_info.lower()
    
    # Check for explicitly restricted licenses
    for restricted in RESTRICTED_LICENSES:
        if restricted in license_lower:
            return False
    
    # Check for allowed license types
    for allowed in PUBLIC_DISPLAY_LICENSES:
        if allowed in license_lower:
            return True
    
    # Check for allowed license URLs
    for allowed_url in PUBLIC_DISPLAY_LICENSE_URLS:
        if allowed_url in license_lower:
            return True
    
    # If it's a URL but not in our allowed list, check for common patterns
    if license_lower.startswith("http"):
        if "creativecommons.org" in license_lower:
            # Most Creative Commons licenses allow public display
            if "by-nc-nd" not in license_lower:  # Except the most restrictive one
                return True
    
    # Default to False for safety
    return False

def get_license_attribution(license_info: Optional[str]) -> str:
    """
    Get the proper attribution text for a license.
    
    Args:
        license_info: License string or URL
        
    Returns:
        str: Attribution text to display
    """
    if not license_info:
        return "License information unavailable"
    
    license_lower = license_info.lower()
    
    # For CC licenses
    if "creativecommons.org" in license_lower or "cc-by" in license_lower or "cc by" in license_lower:
        return "This content is licensed under a Creative Commons license which requires attribution to the original author(s)."
    
    # For public domain
    if "public domain" in license_lower or "cc0" in license_lower:
        return "This content is in the public domain."
    
    # For arXiv
    if "arxiv" in license_lower:
        return "This content is distributed under the arXiv.org license, which allows redistribution with proper attribution."
    
    # Default
    return f"This content is licensed under: {license_info}"