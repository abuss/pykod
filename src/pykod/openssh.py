"""OpenSSH configuration management for pykod."""

from dataclasses import dataclass, field


@dataclass
class OpenSSH:
    """OpenSSH configuration for SSH key management.

    Simple SSH key tracker focused on authorized keys deployment.
    
    Args:
        keys: List of SSH public keys for authentication
    """

    keys: list[str] = field(default_factory=list)

    def to_authorized_keys(self) -> str:
        """Export keys in authorized_keys file format.
        
        Returns:
            String content suitable for authorized_keys file
        """
        valid_keys = [key for key in self.keys if self._is_valid_key(key)]
        if not valid_keys:
            return ""
        return "\n".join(valid_keys) + "\n"

    def _is_valid_key(self, key: str) -> bool:
        """Basic SSH public key format validation.
        
        Args:
            key: SSH public key string
            
        Returns:
            True if key appears to be valid format
        """
        if not key or not isinstance(key, str):
            return False
            
        parts = key.strip().split()
        if len(parts) < 2:
            return False
            
        # Check for common SSH key types
        valid_types = {
            "ssh-rsa", "ssh-dss", "ssh-ed25519", 
            "ecdsa-sha2-nistp256", "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521"
        }
        
        return parts[0] in valid_types