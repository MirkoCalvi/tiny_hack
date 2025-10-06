# Dataset Management Tool

This tool provides comprehensive functionality for managing image datasets in folder format, where each subfolder represents a class label.

## Features

### 1. Class Label Management
- **Update class labels**: Rename existing class folders
- **Create new classes**: Add new empty class folders
- **Move images between classes**: Transfer images from one class to another

### 2. Dataset Analysis
- **View current classes**: List all existing class labels
- **Class statistics**: Get image counts per class
- **Dataset overview**: Complete dataset structure information

### 3. Dataset Splitting
- **Train/Validation/Test split**: Automatically split dataset into training, validation, and test sets
- **Customizable ratios**: Default 70/20/10 split, but fully customizable
- **Reproducible splits**: Option to use random seed for consistent results
- **Organized output**: Creates structured output with separate folders for each split

## Usage

### Basic Usage (Interactive Menu)

```python
from dataloader.data_splitter import DatasetManager

# Initialize with your dataset path
manager = DatasetManager("path/to/your/dataset")

# Use the interactive menu (run the main function)
python src/dataloader/data_splitter.py
```

### Programmatic Usage

```python
from dataloader.data_splitter import DatasetManager

# Initialize dataset manager
manager = DatasetManager("datasets/Face emotion classification.v3i.folder")

# 1. Check current classes and statistics
classes = manager.get_current_classes()
stats = manager.get_class_statistics()
print(f"Classes: {classes}")
print(f"Statistics: {stats}")

# 2. Update a class label
manager.update_class_label("old_name", "new_name")

# 3. Create a new class
manager.create_new_class("neutral")

# 4. Move specific images between classes
image_list = ["image1.jpg", "image2.jpg"]
manager.move_images_to_class("source_class", "target_class", image_list)

# 5. Move all images from one class to another
manager.move_images_to_class("source_class", "target_class")

# 6. Split dataset into train/val/test
manager.split_dataset(
    output_path="outputs",
    dataset_name="my_dataset_split",
    train_ratio=0.7,
    val_ratio=0.2,
    test_ratio=0.1,
    random_seed=42
)
```

### Example Usage Script

Run the example script to see the tool in action:

```bash
python src/dataset_example.py
```

This provides both automated examples and an interactive demo mode.

## Dataset Structure

### Input Format
```
dataset_folder/
├── class1/
│   ├── image1.jpg
│   ├── image2.png
│   └── ...
├── class2/
│   ├── image3.jpg
│   ├── image4.png
│   └── ...
└── class3/
    ├── image5.jpg
    └── ...
```

### Output Format (after splitting)
```
output_folder/dataset_name/
├── train/
│   ├── class1/
│   │   ├── image1.jpg
│   │   └── ...
│   ├── class2/
│   │   └── ...
│   └── class3/
│       └── ...
├── val/
│   ├── class1/
│   ├── class2/
│   └── class3/
└── test/
    ├── class1/
    ├── class2/
    └── class3/
```

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff)
- WebP (.webp)

## Key Methods

### DatasetManager Class

#### `__init__(dataset_path: str)`
Initialize the dataset manager with the path to your dataset folder.

#### `get_current_classes() -> List[str]`
Returns a list of all current class names (folder names).

#### `get_class_statistics() -> Dict[str, int]`
Returns a dictionary mapping class names to image counts.

#### `update_class_label(old_label: str, new_label: str) -> bool`
Rename a class folder from `old_label` to `new_label`.

#### `move_images_to_class(source_class: str, target_class: str, image_names: Optional[List[str]] = None) -> bool`
Move images from `source_class` to `target_class`. If `image_names` is None, moves all images.

#### `create_new_class(class_name: str) -> bool`
Create a new empty class folder with the given name.

#### `split_dataset(output_path: str, dataset_name: str, train_ratio: float = 0.7, val_ratio: float = 0.2, test_ratio: float = 0.1, random_seed: Optional[int] = None) -> bool`
Split the dataset into train/validation/test sets with the specified ratios.

## Example Workflow

1. **Load and inspect dataset**:
   ```python
   manager = DatasetManager("my_dataset")
   print("Classes:", manager.get_current_classes())
   print("Stats:", manager.get_class_statistics())
   ```

2. **Clean up class labels** (if needed):
   ```python
   manager.update_class_label("angry_face", "angry")
   manager.update_class_label("happy_face", "happy")
   ```

3. **Reorganize data** (if needed):
   ```python
   # Move some "angry" images to "frustrated" class
   manager.create_new_class("frustrated")
   specific_images = ["angry_img_1.jpg", "angry_img_5.jpg"]
   manager.move_images_to_class("angry", "frustrated", specific_images)
   ```

4. **Split for training**:
   ```python
   manager.split_dataset(
       output_path="training_data",
       dataset_name="emotion_classification_v1",
       random_seed=42  # For reproducible results
   )
   ```

## Notes

- All operations on class labels and image moving happen in the original dataset folder
- The split operation creates copies in the output directory, leaving the original intact
- Empty folders are automatically removed when all images are moved out
- Name conflicts are handled automatically by appending numbers to filenames
- The tool validates split ratios to ensure they sum to 1.0
- Random seeds ensure reproducible dataset splits for consistent training results