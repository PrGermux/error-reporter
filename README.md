# Error Reporter

This Python project is a comprehensive data analysis and visualization tool built with Python, leveraging PyQt5 for the graphical user interface and Matplotlib for data plotting. The application is specifically designed to manage, aggregate, and visualize error data from various industrial machines, offering both tabular and graphical representations of the data.

### Key Features:
- **Multi-Tab Interface**: The application has multiple tabs for different views of error analysis, including single machine and multiple machine data import options.
- **Error Aggregation and Filtering**: Supports filtering error data by various parameters and aggregating metrics from different machines to identify common issues.
- **Dynamic Plotting**: Utilizes Matplotlib to create dynamic, interactive plots with annotations showing the occurrence and duration of errors.
- **Customizable Plots**: Allows customization of plots, including setting colors and grid configurations for clarity and better user understanding.
- **Data Integration**: Combines error data from CSV files, ensuring comprehensive analysis across different machines.

### Usage
This tool is highly useful for production managers, quality control engineers, and data analysts who need to monitor, analyze, and report on machine errors and performance. By providing both numerical summaries and graphical visualizations, the application helps in identifying trends, recurring errors, and areas for improvement in production processes.

### Python Branch and Complexity
- **Python Branch**: This project utilizes several advanced Python libraries, including PyQt5 for GUI development, Pandas for data manipulation, and Matplotlib for plotting. These libraries indicate a high-level proficiency in Python, especially in data analysis and visualization domains.
- **Complexity**: The project is moderately complex, involving GUI design, data processing, and dynamic plotting. The integration of multiple data sources and the need for interactive and annotated visualizations add to its complexity. The code demonstrates good practices in object-oriented programming and modular design.

### Code Structure
- **Main Interface**: The main GUI is structured using QTabWidget to separate different views for single and multiple machine error analysis.
- **Data Handling**: Data is read from CSV files, cleaned, and aggregated using Pandas.
- **Plotting**: Matplotlib is used extensively for creating detailed plots with annotations and custom legends.

### Future Enhancements
- **Real-Time Data Integration**: Incorporate real-time data fetching and updating mechanisms.
- **Enhanced Customization**: Allow users to customize plots and reports further through the GUI.
- **Additional Data Sources**: Extend support for other data formats and sources, such as databases or APIs.

This repository is a valuable resource for professionals in manufacturing and production environments, providing powerful tools for data-driven decision-making and operational efficiency improvements.

### Screenshots

![grafik](https://github.com/PrGermux/error-reporter/assets/11144116/9f440435-50e5-43fa-b88f-92c1782fc824)
![grafik](https://github.com/PrGermux/error-reporter/assets/11144116/d1e33fa0-787d-4997-852f-9903601246b4)
![grafik](https://github.com/PrGermux/error-reporter/assets/11144116/218396a5-a862-408f-883c-4593fbb19288)
![grafik](https://github.com/PrGermux/error-reporter/assets/11144116/5a6ac7f0-b423-4cc8-b713-38643208b028)


## Installation
1. Clone the repository:
```sh
git clone https://github.com/PrGermux/error-reporter.git
cd quality-control
```
2. Install the required packages:
```sh
pip install -r requirements.txt
```

## Usage
**WARNING:** This program works only with specific data files. The user must adjust each tab to his/her needs with respect to the structure of the input file.

Run the main application:
```sh
python main.py
```

## Freezing
Run the code in a command line:
```sh
pyinstaller --onefile --windowed --icon=icon.png --add-data "icon.png;." --hidden-import=scipy.special._cdflib --name "Error Reporter" main.py
```

## Dependencies
- Python 3.x
- PyQt5
- Pandas
- Matplotlib

## License
This project is licensed under the MIT License for non-commercial use.
