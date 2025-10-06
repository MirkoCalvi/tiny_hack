import random
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional


class DatasetManager:
    """
    A class to manage dataset operations including class label updates and train/val/test splitting.
    
    Handles datasets in folder format where each subfolder represents a class label.
    """
    
    def __init__(self, dataset_path: str):
        """
        Initialize the DatasetManager.
        
        Args:
            dataset_path (str): Path to the dataset folder containing class subfolders
        """
        self.dataset_path = Path(dataset_path)
        if not self.dataset_path.exists():
            raise ValueError(f"Dataset path {dataset_path} does not exist")
        
        self.supported_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    
    def get_current_classes(self) -> List[str]:
        """
        Get list of current class labels (folder names) in the dataset.
        
        Returns:
            List[str]: List of class names
        """
        classes = []
        for item in self.dataset_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                classes.append(item.name)
        return sorted(classes)
    
    def get_class_statistics(self) -> Dict[str, int]:
        """
        Get statistics of images per class.
        
        Returns:
            Dict[str, int]: Dictionary mapping class names to image counts
        """
        stats = {}
        for class_folder in self.dataset_path.iterdir():
            if class_folder.is_dir() and not class_folder.name.startswith('.'):
                image_count = len([f for f in class_folder.iterdir() 
                                 if f.is_file() and f.suffix.lower() in self.supported_extensions])
                stats[class_folder.name] = image_count
        return stats
    
    def update_class_label(self, old_label: str, new_label: str) -> bool:
        """
        Update a class label by renaming the folder.
        
        Args:
            old_label (str): Current class label (folder name)
            new_label (str): New class label (folder name)
            
        Returns:
            bool: True if successful, False otherwise
        """
        old_path = self.dataset_path / old_label
        new_path = self.dataset_path / new_label
        
        if not old_path.exists():
            print(f"Error: Class '{old_label}' does not exist")
            return False
        
        if new_path.exists():
            print(f"Error: Class '{new_label}' already exists")
            return False
        
        try:
            old_path.rename(new_path)
            print(f"Successfully renamed class '{old_label}' to '{new_label}'")
            return True
        except (OSError, PermissionError) as e:
            print(f"Error renaming class: {e}")
            return False
    
    def move_images_to_class(self, source_class: str, target_class: str, 
                           image_names: Optional[List[str]] = None) -> bool:
        """
        Move images from one class to another.
        
        Args:
            source_class (str): Source class folder name
            target_class (str): Target class folder name
            image_names (Optional[List[str]]): Specific image names to move. If None, moves all images.
            
        Returns:
            bool: True if successful, False otherwise
        """
        source_path = self.dataset_path / source_class
        target_path = self.dataset_path / target_class
        
        if not source_path.exists():
            print(f"Error: Source class '{source_class}' does not exist")
            return False
        
        # Create target class folder if it doesn't exist
        target_path.mkdir(exist_ok=True)
        
        try:
            if image_names is None:
                # Move all images
                image_files = [f for f in source_path.iterdir() 
                             if f.is_file() and f.suffix.lower() in self.supported_extensions]
            else:
                # Move specific images
                image_files = []
                for img_name in image_names:
                    img_path = source_path / img_name
                    if img_path.exists() and img_path.suffix.lower() in self.supported_extensions:
                        image_files.append(img_path)
                    else:
                        print(f"Warning: Image '{img_name}' not found in '{source_class}'")
            
            moved_count = 0
            for img_file in image_files:
                target_file = target_path / img_file.name
                # Handle name conflicts
                counter = 1
                while target_file.exists():
                    stem = img_file.stem
                    suffix = img_file.suffix
                    target_file = target_path / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                shutil.move(str(img_file), str(target_file))
                moved_count += 1
            
            print(f"Successfully moved {moved_count} images from '{source_class}' to '{target_class}'")
            
            # Remove source folder if empty
            if not any(source_path.iterdir()):
                source_path.rmdir()
                print(f"Removed empty folder '{source_class}'")
            
            return True
        
        except (OSError, PermissionError, shutil.Error) as e:
            print(f"Error moving images: {e}")
            return False
    
    def create_new_class(self, class_name: str) -> bool:
        """
        Create a new empty class folder.
        
        Args:
            class_name (str): Name of the new class
            
        Returns:
            bool: True if successful, False otherwise
        """
        class_path = self.dataset_path / class_name
        
        if class_path.exists():
            print(f"Error: Class '{class_name}' already exists")
            return False
        
        try:
            class_path.mkdir()
            print(f"Successfully created new class '{class_name}'")
            return True
        except (OSError, PermissionError) as e:
            print(f"Error creating class: {e}")
            return False
    
    def copy_all_to_total_class(self, total_class_name: str = "total") -> bool:
        """
        Copy all images from all existing classes into a new class folder.
        
        Args:
            total_class_name (str): Name of the target class to copy all images to (default: "total")
            
        Returns:
            bool: True if successful, False otherwise
        """
        target_path = self.dataset_path / total_class_name
        
        # Create target class folder if it doesn't exist
        target_path.mkdir(exist_ok=True)
        
        classes = self.get_current_classes()
        
        # Filter out the target class itself to avoid copying to itself
        source_classes = [cls for cls in classes if cls != total_class_name]
        
        if not source_classes:
            print("Error: No source classes found to copy from")
            return False
        
        try:
            total_copied = 0
            copy_stats = {}
            
            for class_name in source_classes:
                class_path = self.dataset_path / class_name
                
                # Get all image files in the class
                image_files = [f for f in class_path.iterdir() 
                             if f.is_file() and f.suffix.lower() in self.supported_extensions]
                
                if not image_files:
                    print(f"Warning: No images found in class '{class_name}', skipping...")
                    copy_stats[class_name] = 0
                    continue
                
                copied_count = 0
                for img_file in image_files:
                    # Create a unique name by prefixing with the original class name
                    new_name = f"{class_name}_{img_file.name}"
                    target_file = target_path / new_name
                    
                    # Handle name conflicts by adding a counter
                    counter = 1
                    while target_file.exists():
                        stem = img_file.stem
                        suffix = img_file.suffix
                        new_name = f"{class_name}_{stem}_{counter}{suffix}"
                        target_file = target_path / new_name
                        counter += 1
                    
                    try:
                        shutil.copy2(str(img_file), str(target_file))
                        copied_count += 1
                        total_copied += 1
                    except (OSError, PermissionError, shutil.Error) as e:
                        print(f"Warning: Could not copy '{img_file.name}' from '{class_name}': {e}")
                
                copy_stats[class_name] = copied_count
                print(f"Copied {copied_count} images from class '{class_name}'")
            
            print(f"\nSuccessfully created '{total_class_name}' class with {total_copied} total images")
            print("Copy statistics:")
            for class_name, count in copy_stats.items():
                if count > 0:
                    print(f"  {class_name}: {count} images")
            
            return True
            
        except (OSError, PermissionError, shutil.Error) as e:
            print(f"Error during copying operation: {e}")
            return False

    def delete_images_from_class(self, class_name: str, num_images: int, 
                               random_selection: bool = True, 
                               specific_images: Optional[List[str]] = None) -> bool:
        """
        Delete a specified number of images from a target class.
        Args:
            class_name (str): Name of the class to delete images from
            num_images (int): Number of images to delete
            random_selection (bool): If True, randomly select images to delete. If False, delete in alphabetical order.
            specific_images (Optional[List[str]]): Specific image names to delete. If provided, ignores num_images and random_selection.
            
        Returns:
            bool: True if successful, False otherwise
        """
        class_path = self.dataset_path / class_name
        
        if not class_path.exists():
            print(f"Error: Class '{class_name}' does not exist")
            return False
        
        # Get all image files in the class
        image_files = [f for f in class_path.iterdir() 
                      if f.is_file() and f.suffix.lower() in self.supported_extensions]
        
        if not image_files:
            print(f"Error: No images found in class '{class_name}'")
            return False
        
        try:
            if specific_images is not None:
                # Delete specific images
                files_to_delete = []
                for img_name in specific_images:
                    img_path = class_path / img_name
                    if img_path.exists() and img_path.suffix.lower() in self.supported_extensions:
                        files_to_delete.append(img_path)
                    else:
                        print(f"Warning: Image '{img_name}' not found in '{class_name}'")
            else:
                # Delete specified number of images
                if num_images <= 0:
                    print(f"Error: Number of images to delete must be positive, got {num_images}")
                    return False
                
                if num_images > len(image_files):
                    print(f"Warning: Requested to delete {num_images} images, but only {len(image_files)} available")
                    num_images = len(image_files)
                
                if random_selection:
                    # Randomly select images to delete
                    random.shuffle(image_files)
                    files_to_delete = image_files[:num_images]
                else:
                    # Delete in alphabetical order
                    image_files.sort(key=lambda x: x.name.lower())
                    files_to_delete = image_files[:num_images]
            
            # Delete the selected files
            deleted_count = 0
            for img_file in files_to_delete:
                try:
                    img_file.unlink()
                    deleted_count += 1
                except (OSError, PermissionError) as e:
                    print(f"Warning: Could not delete '{img_file.name}': {e}")
            
            print(f"Successfully deleted {deleted_count} images from class '{class_name}'")
            
            # Check if class folder is now empty
            remaining_files = [f for f in class_path.iterdir() 
                             if f.is_file() and f.suffix.lower() in self.supported_extensions]
            
            if not remaining_files:
                print(f"Class '{class_name}' now has no images remaining")
            else:
                print(f"Class '{class_name}' now has {len(remaining_files)} images remaining")
            
            return True
            
        except (OSError, PermissionError) as e:
            print(f"Error deleting images from class '{class_name}': {e}")
            return False
    
    def split_dataset(self, output_path: str, dataset_name: str, 
                     train_ratio: float = 0.7, val_ratio: float = 0.2, 
                     test_ratio: float = 0.1, random_seed: Optional[int] = None) -> bool:
        """
        Split the dataset into train/validation/test sets.
        
        Args:
            output_path (str): Path where the split dataset will be saved
            dataset_name (str): Name of the dataset (used as folder name)
            train_ratio (float): Proportion for training set (default: 0.7)
            val_ratio (float): Proportion for validation set (default: 0.2)
            test_ratio (float): Proportion for test set (default: 0.1)
            random_seed (Optional[int]): Random seed for reproducible splits
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Validate ratios
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            print("Error: Train, validation, and test ratios must sum to 1.0")
            return False
        
        if random_seed is not None:
            random.seed(random_seed)
        
        output_base = Path(output_path) / dataset_name
        train_dir = output_base / "train"
        val_dir = output_base / "val"
        test_dir = output_base / "test"
        
        try:
            # Create output directories
            for split_dir in [train_dir, val_dir, test_dir]:
                split_dir.mkdir(parents=True, exist_ok=True)
            
            classes = self.get_current_classes()
            if not classes:
                print("Error: No classes found in the dataset")
                return False
            
            total_images = 0
            split_stats = defaultdict(lambda: {'train': 0, 'val': 0, 'test': 0})
            
            for class_name in classes:
                class_path = self.dataset_path / class_name
                
                # Get all image files in the class
                image_files = [f for f in class_path.iterdir() 
                             if f.is_file() and f.suffix.lower() in self.supported_extensions]
                
                if not image_files:
                    print(f"Warning: No images found in class '{class_name}', skipping...")
                    continue
                
                # Shuffle images for random splitting
                random.shuffle(image_files)
                
                n_images = len(image_files)
                n_train = int(n_images * train_ratio)
                n_val = int(n_images * val_ratio)
                n_test = n_images - n_train - n_val  # Ensure all images are used
                
                # Create class directories in each split
                for split_dir in [train_dir, val_dir, test_dir]:
                    (split_dir / class_name).mkdir(exist_ok=True)
                
                # Copy images to respective splits
                splits = [
                    (image_files[:n_train], train_dir / class_name, 'train'),
                    (image_files[n_train:n_train + n_val], val_dir / class_name, 'val'),
                    (image_files[n_train + n_val:n_train + n_val + n_test], test_dir / class_name, 'test')
                ]
                
                for images, target_dir, split_name in splits:
                    for img_file in images:
                        shutil.copy2(str(img_file), str(target_dir / img_file.name))
                    split_stats[class_name][split_name] = len(images)
                
                total_images += n_images
            
            # Print statistics
            print("\nDataset split completed successfully!")
            print(f"Output directory: {output_base}")
            print(f"Total images processed: {total_images}")
            print(f"\nSplit ratios: Train={train_ratio:.1%}, Val={val_ratio:.1%}, Test={test_ratio:.1%}")
            print("\nPer-class distribution:")
            print(f"{'Class':<20} {'Train':<8} {'Val':<8} {'Test':<8} {'Total':<8}")
            print("-" * 56)
            
            for class_name in sorted(split_stats.keys()):
                stats = split_stats[class_name]
                total_class = sum(stats.values())
                print(f"{class_name:<20} {stats['train']:<8} {stats['val']:<8} {stats['test']:<8} {total_class:<8}")
            
            return True
            
        except (OSError, PermissionError, shutil.Error) as e:
            print(f"Error during dataset splitting: {e}")
            return False


def main():
    """
    Example usage of the DatasetManager class.
    """
    # Example usage
    dataset_path = input("Enter dataset path: ").strip()
    
    if not dataset_path:
        print("No dataset path provided, exiting...")
        return
    
    try:
        manager = DatasetManager(dataset_path)
        
        while True:
            print("\n" + "="*50)
            print("Dataset Manager Menu:")
            print("1. Show current classes and statistics")
            print("2. Update class label")
            print("3. Move images between classes")
            print("4. Create new class")
            print("5. Delete images from class")
            print("6. Copy all images to 'total' class")
            print("7. Split dataset (train/val/test)")
            print("8. Exit")
            print("="*50)
            
            choice = input("Enter your choice (1-8): ").strip()
            
            if choice == '1':
                classes = manager.get_current_classes()
                stats = manager.get_class_statistics()
                print(f"\nCurrent classes ({len(classes)}):")
                for class_name in classes:
                    print(f"  {class_name}: {stats[class_name]} images")
            
            elif choice == '2':
                old_label = input("Enter current class label: ").strip()
                new_label = input("Enter new class label: ").strip()
                manager.update_class_label(old_label, new_label)
            
            elif choice == '3':
                source = input("Enter source class: ").strip()
                target = input("Enter target class: ").strip()
                move_all = input("Move all images? (y/n): ").strip().lower() == 'y'
                
                if move_all:
                    manager.move_images_to_class(source, target)
                else:
                    images_input = input("Enter image names (comma-separated): ").strip()
                    image_names = [img.strip() for img in images_input.split(',')] if images_input else None
                    manager.move_images_to_class(source, target, image_names)
            
            elif choice == '4':
                class_name = input("Enter new class name: ").strip()
                manager.create_new_class(class_name)
            
            elif choice == '5':
                class_name = input("Enter class name to delete images from: ").strip()
                
                # Show current class statistics
                stats = manager.get_class_statistics()
                if class_name in stats:
                    print(f"Class '{class_name}' currently has {stats[class_name]} images")
                else:
                    print(f"Error: Class '{class_name}' not found")
                    continue
                
                delete_specific = input("Delete specific images by name? (y/n): ").strip().lower() == 'y'
                
                if delete_specific:
                    images_input = input("Enter image names to delete (comma-separated): ").strip()
                    if images_input:
                        image_names = [img.strip() for img in images_input.split(',')]
                        manager.delete_images_from_class(class_name, 0, specific_images=image_names)
                    else:
                        print("No image names provided")
                else:
                    try:
                        num_to_delete = int(input("Enter number of images to delete: ").strip())
                        random_selection = input("Random selection? (y/n, default=y): ").strip().lower() != 'n'
                        manager.delete_images_from_class(class_name, num_to_delete, random_selection)
                    except ValueError:
                        print("Invalid number entered")
            
            elif choice == '6':
                # Show current classes before copying
                classes = manager.get_current_classes()
                stats = manager.get_class_statistics()
                print(f"\nCurrent classes to copy from ({len(classes)}):")
                for class_name in classes:
                    print(f"  {class_name}: {stats[class_name]} images")
                
                total_class_name = input("\nEnter name for the total class (default='total'): ").strip()
                if not total_class_name:
                    total_class_name = "total"
                
                confirm = input(f"Copy all images from all classes to '{total_class_name}'? (y/n): ").strip().lower()
                if confirm == 'y':
                    manager.copy_all_to_total_class(total_class_name)
                else:
                    print("Operation cancelled")
            
            elif choice == '7':
                output_path = input("Enter output directory path: ").strip()
                dataset_name = input("Enter dataset name: ").strip()
                
                # Ask for custom ratios or use defaults
                use_custom = input("Use custom split ratios? (y/n, default uses 70/20/10): ").strip().lower() == 'y'
                
                if use_custom:
                    try:
                        train_ratio = float(input("Enter train ratio (0.0-1.0): ").strip())
                        val_ratio = float(input("Enter validation ratio (0.0-1.0): ").strip())
                        test_ratio = float(input("Enter test ratio (0.0-1.0): ").strip())
                    except ValueError:
                        print("Invalid ratio values, using defaults (70/20/10)")
                        train_ratio, val_ratio, test_ratio = 0.7, 0.2, 0.1
                else:
                    train_ratio, val_ratio, test_ratio = 0.7, 0.2, 0.1
                
                # Ask for random seed
                seed_input = input("Enter random seed (optional, press Enter to skip): ").strip()
                random_seed = int(seed_input) if seed_input else None
                
                manager.split_dataset(output_path, dataset_name, train_ratio, val_ratio, test_ratio, random_seed)
            
            elif choice == '8':
                print("Goodbye!")
                break
            
            else:
                print("Invalid choice. Please try again.")
    
    except (ValueError, OSError, PermissionError) as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
