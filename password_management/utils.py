import os
import base64
import hashlib
import secrets
import re
import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from django.conf import settings
from django.utils.crypto import get_random_string

class PasswordEncryption:
    """Handles encryption and decryption of password data using AES-256-CBC."""
    
    @staticmethod
    def generate_key(master_password, salt, iterations=100000):
        """
        Generate a key from the master password using PBKDF2.
        
        Args:
            master_password (str): The user's master password
            salt (str): Salt value for key derivation
            iterations (int): Number of iterations for key derivation
            
        Returns:
            bytes: 32-byte key for AES-256
        """
        if isinstance(master_password, str):
            master_password = master_password.encode('utf-8')
        
        if isinstance(salt, str):
            salt = salt.encode('utf-8')
            
        return hashlib.pbkdf2_hmac(
            'sha256', 
            master_password, 
            salt, 
            iterations, 
            dklen=32
        )
    
    @staticmethod
    def generate_iv():
        """
        Generate a random initialization vector for AES-CBC mode.
        
        Returns:
            bytes: 16-byte initialization vector
        """
        return os.urandom(16)
    
    @staticmethod
    def encrypt(data, key, iv=None):
        """
        Encrypt data using AES-256-CBC.
        
        Args:
            data (str): The data to encrypt
            key (bytes): 32-byte encryption key
            iv (bytes, optional): Initialization vector. Generated if not provided.
            
        Returns:
            tuple: (encrypted_data, iv)
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        if iv is None:
            iv = PasswordEncryption.generate_iv()
            
        # Pad data to block size
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # Create cipher and encrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        return encrypted_data, iv
    
    @staticmethod
    def decrypt(encrypted_data, key, iv):
        """
        Decrypt data using AES-256-CBC.
        
        Args:
            encrypted_data (bytes): The encrypted data
            key (bytes): 32-byte encryption key
            iv (bytes): Initialization vector used for encryption
            
        Returns:
            str: Decrypted data as a string
        """
        # Create cipher and decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # Unpad the decrypted data
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data.decode('utf-8')


class PasswordSecurity:
    """Tools for checking password strength, breach status, etc."""
    
    @staticmethod
    def check_password_strength(password):
        """
        Evaluate password strength based on various criteria.
        
        Args:
            password (str): The password to evaluate
            
        Returns:
            tuple: (strength_category, score)
            where strength_category is one of: weak, medium, strong, very_strong
        """
        # Calculate initial score
        score = 0
        
        # Length check (up to 20 characters max score)
        length_score = min(len(password) * 0.5, 10)
        score += length_score
        
        # Character diversity checks
        if re.search(r'[A-Z]', password):
            score += 2  # Uppercase letters
        if re.search(r'[a-z]', password):
            score += 2  # Lowercase letters
        if re.search(r'[0-9]', password):
            score += 2  # Numbers
        if re.search(r'[^A-Za-z0-9]', password):
            score += 3  # Special characters
            
        # Variety checks
        unique_chars = len(set(password))
        variety_score = min(unique_chars * 0.5, 5)
        score += variety_score
        
        # Penalty for patterns
        # Check for sequences
        for i in range(len(password) - 2):
            if (ord(password[i+1]) == ord(password[i]) + 1 and 
                    ord(password[i+2]) == ord(password[i]) + 2):
                score -= 3
                break
                
        # Check for repeated characters
        for i in range(len(password) - 2):
            if password[i] == password[i+1] and password[i] == password[i+2]:
                score -= 3
                break
        
        # Classify strength based on score
        if score < 10:
            return 'weak', score
        elif score < 15:
            return 'medium', score
        elif score < 20:
            return 'strong', score
        else:
            return 'very_strong', score
    
    @staticmethod
    def generate_secure_password(length=16, uppercase=True, numbers=True, symbols=True):
        """
        Generate a cryptographically secure random password.
        
        Args:
            length (int): Length of the password
            uppercase (bool): Include uppercase letters
            numbers (bool): Include numbers
            symbols (bool): Include special characters
            
        Returns:
            str: A random password
        """
        # Set up character sets
        lowercase_chars = 'abcdefghijklmnopqrstuvwxyz'
        uppercase_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if uppercase else ''
        number_chars = '0123456789' if numbers else ''
        symbol_chars = '!@#$%^&*()-_=+[]{}|;:,.<>?' if symbols else ''
        
        # Ensure at least one character from each enabled set
        all_chars = lowercase_chars + uppercase_chars + number_chars + symbol_chars
        password = []
        
        # Add one character from each enabled set
        password.append(secrets.choice(lowercase_chars))
        if uppercase:
            password.append(secrets.choice(uppercase_chars))
        if numbers:
            password.append(secrets.choice(number_chars))
        if symbols:
            password.append(secrets.choice(symbol_chars))
            
        # Fill the rest with random characters from all sets
        remaining_length = length - len(password)
        password.extend(secrets.choice(all_chars) for _ in range(remaining_length))
        
        # Shuffle the password to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    @staticmethod
    def check_haveibeenpwned(password):
        """
        Check if a password has been exposed in data breaches using HaveIBeenPwned API.
        Uses k-anonymity to protect the full password.
        
        Args:
            password (str): The password to check
            
        Returns:
            tuple: (is_compromised, count) where count is the number of times the password
                  appeared in breaches, or None if the request failed
        """
        # Create a SHA-1 hash of the password
        password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        # Take the first 5 characters of the hash
        prefix = password_hash[:5]
        # The rest of the hash for comparison
        suffix = password_hash[5:]
        
        try:
            # Query the API with the prefix
            response = requests.get(f'https://api.pwnedpasswords.com/range/{prefix}')
            if response.status_code == 200:
                # Check if the suffix is in the response
                for line in response.text.splitlines():
                    parts = line.split(':')
                    if len(parts) == 2 and parts[0] == suffix:
                        return True, int(parts[1])
                return False, 0
            else:
                return None, None
        except Exception:
            return None, None


def create_master_password_hash(password):
    """
    Create a secure hash for the master password.
    
    Args:
        password (str): The master password
        
    Returns:
        tuple: (hash, salt, iterations)
    """
    salt = base64.b64encode(os.urandom(32)).decode('utf-8')
    iterations = 100000  # This should be adjusted based on security needs
    
    hash_value = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        iterations, 
        dklen=32
    )
    hash_value = base64.b64encode(hash_value).decode('utf-8')
    
    return hash_value, salt, iterations


def verify_master_password(password, stored_hash, salt, iterations):
    """
    Verify if the provided master password matches the stored hash.
    
    Args:
        password (str): The password to verify
        stored_hash (str): The stored hash value
        salt (str): The salt used for hashing
        iterations (int): The number of iterations used
        
    Returns:
        bool: True if the password matches, False otherwise
    """
    hash_value = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        iterations, 
        dklen=32
    )
    hash_value = base64.b64encode(hash_value).decode('utf-8')
    
    return secrets.compare_digest(hash_value, stored_hash) 