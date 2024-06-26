import sys
import os
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog, QTabWidget, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QHBoxLayout, QLabel, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class BlockDiagramCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots(figsize=(12, 4))  # Adjusted figsize for tighter plot
        self.fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.17)  # Adjust subplots to remove outer borders
        super().__init__(self.fig)
        self.setParent(parent)
        self.process_intervals = []

    def add_interval(self, start_time, end_time, color):
        duration = end_time - start_time
        if duration.total_seconds() > 0:
            self.process_intervals.append((start_time, duration, color))

    def plot(self, data, start_time, end_time, day_view=False, process_pair=None, color_sequence=None, legend_entries=None):
        self.ax.clear()
        block_height = 10

        if process_pair:
            start_processes, end_processes, color = process_pair
            current_start_time = None
            for index, row in data.iterrows():
                msg_text = row['MsgText']
                time = pd.to_datetime(row['TimeString'])
                
                if any(start_process in msg_text for start_process in start_processes):
                    if current_start_time is None:
                        current_start_time = time
                        current_color = color

                if current_start_time is not None and any(end_process in msg_text for end_process in end_processes):
                    self.add_interval(current_start_time, time, current_color)
                    current_start_time = None
                    current_color = None

            # Handle case where process starts but does not end on the same day
            if current_start_time is not None:
                next_day_start = (end_time + pd.Timedelta(seconds=1)).normalize()
                self.add_interval(current_start_time, next_day_start, current_color)

        else:
            current_start_time = None
            for start_processes, end_processes, color in color_sequence:
                for index, row in data.iterrows():
                    msg_text = row['MsgText']
                    time = pd.to_datetime(row['TimeString'])

                    if any(start_process in msg_text for start_process in start_processes):
                        if current_start_time is None:
                            current_start_time = time
                            current_color = color

                    if current_start_time is not None and any(end_process in msg_text for end_process in end_processes):
                        self.add_interval(current_start_time, time, current_color)
                        current_start_time = None
                        current_color = None

            # Add the last interval if it exists
            if current_start_time is not None:
                self.add_interval(current_start_time, end_time, current_color)

        # Plot all intervals
        for start, duration, color in self.process_intervals:
            self.ax.broken_barh([(start, duration)], (0, block_height), facecolors=(color), alpha=0.5)

        # Plot error bars on top of the colored blocks
        for index, row in data.iterrows():
            time = pd.to_datetime(row['TimeString'])
            msg_number = row['MsgNumber']
            if msg_number <= 175:  # Error
                self.ax.vlines(x=time, ymin=0, ymax=block_height, colors='red', alpha=1.0)

        # Adjust axes
        self.ax.set_ylim(0, block_height)
        
        if day_view:
            self.ax.set_xlim(start_time, end_time)
            self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
            self.ax.set_xlabel('Hour')
        else:
            self.ax.set_xlim(start_time, end_time)
            self.ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right")
            self.ax.set_xlabel('Date')

        self.ax.set_yticks([])
        self.ax.grid(False)
        
        # Add legend
        if legend_entries:
            legend_elements = [Patch(facecolor=color, edgecolor='black', label=label) for label, color in legend_entries.items()]
        else:
            legend_elements = [
                Patch(facecolor='cyan', edgecolor='black', label='Set up'),
                Patch(facecolor='blue', edgecolor='black', label='Ventilation'),
                Patch(facecolor='green', edgecolor='black', label='Pump out'),
                Patch(facecolor='orange', edgecolor='black', label='Coating'),
                Patch(facecolor='red', edgecolor='black', label='Error', alpha=1.0)
            ]
        self.ax.legend(handles=legend_elements, loc='upper left')

        self.draw()

class ErrorTable(QWidget):
    def __init__(self, data, parent=None, table_type='count'):
        super().__init__(parent)
        self.data = data
        self.table_type = table_type
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.populate_table()

    def populate_table(self):
        if self.data is not None:
            if self.table_type == 'count':
                error_data = self.data[self.data['MsgNumber'] <= 175]
                error_counts = error_data['MsgText'].value_counts().reset_index()
                error_counts.columns = ['Error Message', 'Count']

                self.table.setRowCount(len(error_counts))
                self.table.setColumnCount(2)
                self.table.setHorizontalHeaderLabels(['Error Message', 'Count'])

                for row in range(len(error_counts)):
                    self.table.setItem(row, 0, QTableWidgetItem(error_counts.iloc[row, 0]))
                    self.table.setItem(row, 1, QTableWidgetItem(str(error_counts.iloc[row, 1])))

            elif self.table_type == 'chronology':
                error_data = self.data[self.data['MsgNumber'] <= 175].sort_values(by='TimeString')
                self.table.setRowCount(len(error_data))
                self.table.setColumnCount(2)
                self.table.setHorizontalHeaderLabels(['Time', 'Error Message'])

                for row in range(len(error_data)):
                    self.table.setItem(row, 0, QTableWidgetItem(error_data.iloc[row]['TimeString'].strftime('%d.%m.%Y %H:%M')))
                    self.table.setItem(row, 1, QTableWidgetItem(error_data.iloc[row]['MsgText']))

            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        else:
            self.table.setRowCount(0)
            self.table.setColumnCount(2)
            if self.table_type == 'count':
                self.table.setHorizontalHeaderLabels(['Error Message', 'Count'])
            elif self.table_type == 'chronology':
                self.table.setHorizontalHeaderLabels(['Time', 'Error Message'])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Error Reporter")
        self.setGeometry(100, 100, 1200, 600)
        self.setWindowIcon(QIcon(resource_path('icon.png')))
        self.data = None
        self.initUI()

    def initUI(self):
        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        self.main_tabs = QTabWidget()
        self.tab_single = QWidget()
        self.tab_multiple = QWidget()

        self.main_tabs.addTab(self.tab_single, "Single")
        self.main_tabs.addTab(self.tab_multiple, "Multiple")

        self.init_single_tab()
        self.init_multiple_tab()

        self.layout.addWidget(self.main_tabs)

    def init_single_tab(self):
        layout = QVBoxLayout(self.tab_single)

        self.button_open = QPushButton("Open CSV File")
        self.button_open.clicked.connect(self.open_file)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.button_open)
        self.button_layout.setAlignment(Qt.AlignTop)
        layout.addLayout(self.button_layout)

        self.tabs = QTabWidget()
        self.tab_day = QWidget()
        self.tab_all = QWidget()

        self.tabs.addTab(self.tab_day, "Day")
        self.tabs.addTab(self.tab_all, "All")

        self.init_day_tab()
        self.init_all_tab()

        layout.addWidget(self.tabs)
        self.tabs.hide()

    def init_multiple_tab(self):
        layout = QVBoxLayout(self.tab_multiple)
        self.file_paths = {}

        self.buttons = ["EPOL0E", "ISD1A", "DECK1A", "SEED1A", "SL1A", "SL1B", "AG1A", "OX1A"]
        self.import_buttons = {}

        for button in self.buttons:
            btn = QPushButton(button)
            btn.clicked.connect(self.import_file)
            layout.addWidget(btn)
            self.import_buttons[button] = btn
            label = QLabel("")
            layout.addWidget(label)
            self.file_paths[button] = label

        self.show_button = QPushButton("Show")
        self.show_button.clicked.connect(self.show_imported_files)
        layout.addWidget(self.show_button)

        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_imported_files)
        layout.addWidget(self.reset_button)

    def import_file(self):
        sender = self.sender().text()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.file_paths[sender].setText(file_path)

    def reset_imported_files(self):
        for button in self.buttons:
            self.file_paths[button].setText("")

    def show_imported_files(self):
        selected_files = {button: self.file_paths[button].text() for button in self.buttons if self.file_paths[button].text()}
        
        if len(selected_files) < 2:
            QMessageBox.warning(self, "Error", "Please import at least two files.")
            return

        common_errors = self.find_common_errors(selected_files.values())
        if not common_errors.empty:
            common_errors.sort_values(by='Date', ascending=False, inplace=True)
            self.display_common_errors(common_errors, " ".join(selected_files.keys()) + " Common Errors")
        else:
            QMessageBox.information(self, "No Common Errors", "No common errors found among the imported files.")

    def find_common_errors(self, file_paths):
        dataframes = [pd.read_csv(file, delimiter=';', encoding='latin1', on_bad_lines='skip') for file in file_paths]

        for df in dataframes:
            df['TimeString'] = pd.to_datetime(df['TimeString'], format='%d.%m.%Y %H:%M')

        common_errors = pd.DataFrame(columns=['Date', 'Error Message', 'Count'])

        for date in pd.to_datetime(dataframes[0]['TimeString']).dt.date.unique():
            errors = []
            for df in dataframes:
                df_on_date = df[pd.to_datetime(df['TimeString']).dt.date == date]
                errors.append(df_on_date[df_on_date['MsgNumber'] <= 175]['MsgText'].value_counts())

            common = errors[0]
            for err in errors[1:]:
                common = common.combine(err, min, fill_value=0)

            for error, count in common[common > 0].items():
                common_errors = pd.concat([common_errors, pd.DataFrame([{'Date': date, 'Error Message': error, 'Count': count}])], ignore_index=True)

        return common_errors

    def display_common_errors(self, common_errors, window_title):
        self.common_errors_window = QMainWindow(self)
        self.common_errors_window.setWindowTitle(window_title)
        self.common_errors_window.setGeometry(150, 150, 800, 600)
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        table = QTableWidget()
        table.setRowCount(len(common_errors))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Date', 'Error Message', 'Count'])

        for row in range(len(common_errors)):
            table.setItem(row, 0, QTableWidgetItem(common_errors.iloc[row, 0].strftime('%d.%m.%Y')))
            table.setItem(row, 1, QTableWidgetItem(common_errors.iloc[row, 1]))
            table.setItem(row, 2, QTableWidgetItem(str(common_errors.iloc[row, 2])))

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)
        self.common_errors_window.setCentralWidget(central_widget)
        self.common_errors_window.show()

    def init_day_tab(self):
        layout = QVBoxLayout(self.tab_day)
        self.date_dropdown = QComboBox()
        self.date_dropdown.currentIndexChanged.connect(self.update_day_tab)
        layout.addWidget(self.date_dropdown)
        self.canvas_day = BlockDiagramCanvas(self.tab_day)
        layout.addWidget(self.canvas_day)

        self.day_tabs = QTabWidget()
        self.day_count_tab = QWidget()
        self.day_chronology_tab = QWidget()

        self.day_tabs.addTab(self.day_count_tab, "Count")
        self.day_tabs.addTab(self.day_chronology_tab, "Chronology")

        self.day_count_layout = QVBoxLayout(self.day_count_tab)
        self.day_chronology_layout = QVBoxLayout(self.day_chronology_tab)

        self.error_table_day_count = ErrorTable(None, self.day_count_tab)
        self.error_table_day_chronology = ErrorTable(None, self.day_chronology_tab, table_type='chronology')

        self.day_count_layout.addWidget(self.error_table_day_count)
        self.day_chronology_layout.addWidget(self.error_table_day_chronology)

        layout.addWidget(self.day_tabs)

    def init_all_tab(self):
        layout = QVBoxLayout(self.tab_all)
        self.canvas_all = BlockDiagramCanvas(self.tab_all)
        layout.addWidget(self.canvas_all)

        self.all_tabs = QTabWidget()
        self.all_count_tab = QWidget()
        self.all_chronology_tab = QWidget()

        self.all_tabs.addTab(self.all_count_tab, "Count")
        self.all_tabs.addTab(self.all_chronology_tab, "Chronology")

        self.all_count_layout = QVBoxLayout(self.all_count_tab)
        self.all_chronology_layout = QVBoxLayout(self.all_chronology_tab)

        self.error_table_all_count = ErrorTable(None, self.all_count_tab)
        self.error_table_all_chronology = ErrorTable(None, self.all_chronology_tab, table_type='chronology')

        self.all_count_layout.addWidget(self.error_table_all_count)
        self.all_chronology_layout.addWidget(self.error_table_all_chronology)

        layout.addWidget(self.all_tabs)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        if file_path:
            try:
                # Use semicolon as the delimiter
                self.data = pd.read_csv(file_path, delimiter=';', encoding='latin1', on_bad_lines='skip')
                self.process_data()
                self.populate_dates()
                self.update_all_tab()
                self.update_day_tab()
                self.tabs.show()  # Show tabs after successful import
            except Exception as e:
                print(f"Failed to read the file: {e}")

    def process_data(self):
        try:
            self.data['TimeString'] = pd.to_datetime(self.data['TimeString'], format='%d.%m.%Y %H:%M')
        except Exception as e:
            print(f"Error processing data: {e}")

    def populate_dates(self):
        unique_dates = self.data['TimeString'].dt.date.unique()
        self.date_dropdown.clear()
        for date in sorted(unique_dates, reverse=True):
            self.date_dropdown.addItem(date.strftime('%d.%m.%Y'))

    def update_day_tab(self):
        selected_date = self.date_dropdown.currentText()
        if selected_date:
            start_time = pd.Timestamp(datetime.strptime(selected_date, '%d.%m.%Y'))
            end_time = start_time + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            day_data = self.get_day_data(start_time, end_time)
            color_sequence = [
                (["Anlagezustand-BM : Quelle einrichten"], ["Anlagezustand-BM : Belüften", "Anlagezustand-VM : Belüften", "Anlagezustand-BM : Abpumpen", "Anlagezustand-VM : Abpumpen", "Anlagezustand-BM : Prozess starten"], 'cyan'),
                (["Anlagezustand-BM : Belüften", "Anlagezustand-VM : Belüften"], ["Anlagezustand-BM : Quelle einrichten", "Anlagezustand-BM : Abpumpen", "Anlagezustand-VM : Abpumpen", "Anlagezustand-BM : Prozess starten"], 'blue'),
                (["Anlagezustand-BM : Abpumpen", "Anlagezustand-VM : Abpumpen"], ["Anlagezustand-BM : Quelle einrichten", "Anlagezustand-BM : Belüften", "Anlagezustand-VM : Belüften", "Anlagezustand-BM : Prozess starten"], 'green'),
                (["Anlagezustand-BM : Prozess starten"], ["Anlagezustand-BM : Prozess beenden"], 'orange')
            ]
            self.canvas_day.plot(day_data, start_time, end_time, day_view=True, color_sequence=color_sequence)
            self.error_table_day_count.data = day_data
            self.error_table_day_count.populate_table()
            self.error_table_day_chronology.data = day_data
            self.error_table_day_chronology.populate_table()

    def update_all_tab(self):
        if self.data is not None:
            start_time = self.data['TimeString'].min().normalize()
            end_time = self.data['TimeString'].max().normalize() + pd.Timedelta(days=1)
            process_pair = (["Anlagezustand-BM : Prozess starten"], ["Anlagezustand-BM : Prozess beenden"], 'orange')
            all_data = self.data
            legend_entries = {'Coating': 'orange', 'Error': 'red'}
            self.canvas_all.plot(all_data, start_time, end_time, day_view=False, process_pair=process_pair, legend_entries=legend_entries)
            self.error_table_all_count.data = all_data
            self.error_table_all_count.populate_table()
            self.error_table_all_chronology.data = all_data
            self.error_table_all_chronology.populate_table()

    def get_day_data(self, start_time, end_time):
        previous_data = self.data[self.data['TimeString'] < start_time]
        day_data = self.data[(self.data['TimeString'] >= start_time) & (self.data['TimeString'] <= end_time)]
        next_data = self.data[self.data['TimeString'] > end_time]

        for start_processes, end_processes, color in [
            (["Anlagezustand-BM : Prozess starten"], ["Anlagezustand-BM : Prozess beenden"], 'orange')
        ]:
            current_start_time = None

            # Check for ongoing processes from the previous day
            for index, row in previous_data.iterrows():
                msg_text = row['MsgText']
                time = pd.to_datetime(row['TimeString'])
                if any(start_process in msg_text for start_process in start_processes):
                    current_start_time = time
                if current_start_time is not None and any(end_process in msg_text for end_process in end_processes):
                    current_start_time = None

            # If an ongoing process is found, extend it to the end of the selected day
            if current_start_time is not None:
                day_data = pd.concat([day_data, pd.DataFrame([{'TimeString': end_time + pd.Timedelta(seconds=1), 'MsgNumber': 60000, 'MsgText': "Ongoing Process"}])], ignore_index=True)

            # Check for processes that start on the selected day and extend to the next day
            for index, row in day_data.iterrows():
                msg_text = row['MsgText']
                time = pd.to_datetime(row['TimeString'])
                if any(start_process in msg_text for start_process in start_processes):
                    current_start_time = time
                if current_start_time is not None and any(end_process in msg_text for end_process in end_processes):
                    current_start_time = None

            # If a process starts on the selected day and continues, add a marker to the next day
            if current_start_time is not None:
                next_data = pd.concat([next_data, pd.DataFrame([{'TimeString': end_time + pd.Timedelta(days=1), 'MsgNumber': 60000, 'MsgText': "Ongoing Process"}])], ignore_index=True)

            # Handle "Anlagezustand-BM : Prozess läuft" logic
            if day_data['MsgText'].str.contains("Anlagezustand-BM : Prozess läuft").any():
                self.canvas_day.add_interval(start_time, end_time, 'orange')

            # Handle "Anlagezustand-BM : Prozess beenden" logic
            first_process_beenden = day_data[day_data['MsgText'].str.contains("Anlagezustand-BM : Prozess beenden")].head(1)
            if not first_process_beenden.empty:
                process_beenden_time = first_process_beenden['TimeString'].iloc[0]
                self.canvas_day.add_interval(start_time, process_beenden_time, 'orange')

        return day_data

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
