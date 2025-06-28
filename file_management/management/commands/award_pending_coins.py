from django.core.management.base import BaseCommand
import math
from file_management.models import UserFile
from coin_wallet.models import CoinWallet, CoinTransaction

class Command(BaseCommand):
    help = 'Award coins for files that have not been awarded coins yet'

    def handle(self, *args, **options):
        files_without_coins = UserFile.objects.filter(coins_awarded=False, file_size__gt=0)
        self.stdout.write(f"Found {files_without_coins.count()} files without coins awarded")
        
        for user_file in files_without_coins:
            try:
                # Calculate coins (1 coin per MB)
                file_size_mb = math.ceil(user_file.file_size / (1024 * 1024))
                if file_size_mb < 1:
                    file_size_mb = 1  # Minimum 1 coin per file
                
                # Get or create the user's wallet
                wallet, created = CoinWallet.objects.get_or_create(user=user_file.user)
                
                # Check if coins were already awarded for this file
                existing_transaction = CoinTransaction.objects.filter(
                    wallet=wallet,
                    transaction_type='upload',
                    related_file=user_file
                ).exists()
                
                if not existing_transaction:
                    # Award coins
                    wallet.add_coins(
                        amount=file_size_mb,
                        transaction_type='upload',
                        source=f'File upload: {user_file.original_filename}'
                    )
                    
                    # Update the transaction with the related file
                    transaction = CoinTransaction.objects.filter(
                        wallet=wallet,
                        transaction_type='upload'
                    ).latest('created_at')
                    transaction.related_file = user_file
                    transaction.save()
                    
                    # Mark coins as awarded
                    user_file.coins_awarded = True
                    user_file.save(update_fields=['coins_awarded'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Awarded {file_size_mb} coins for file '{user_file.original_filename}' (ID: {user_file.id})"
                        )
                    )
                else:
                    # Already awarded but not marked
                    user_file.coins_awarded = True
                    user_file.save(update_fields=['coins_awarded'])
                    
                    self.stdout.write(
                        self.style.WARNING(
                            f"File '{user_file.original_filename}' already had coins awarded, marked as awarded"
                        )
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error awarding coins for file '{user_file.original_filename}' (ID: {user_file.id}): {str(e)}"
                    )
                )
        
        self.stdout.write(self.style.SUCCESS("Finished awarding coins for files")) 