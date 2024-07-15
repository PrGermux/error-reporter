import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog,
                             QTabWidget, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QHBoxLayout,
                             QLabel, QMessageBox, QProgressDialog, QDialog, QProgressBar)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def plot(self, data, start_time, end_time, day_view=False, plot_coating_only=False):
        self.ax.clear()
        block_height = 10
        warning_msg_numbers = list(range(29, 38)) + list(range(58, 66)) + list(range(73, 80)) + list(range(90, 93)) + list(range(125, 141)) + list(range(148, 152)) + [173, 174]

        if plot_coating_only:
            current_start_time = None
            for index, row in data.iterrows():
                msg_text = row['MsgText']
                time = pd.to_datetime(row['TimeString'])

                if "Anlagezustand-BM : Prozess starten" in msg_text:
                    current_start_time = time
                if current_start_time is not None and any(end_process in msg_text for end_process in ["Anlagezustand-BM : Prozess beenden", "Anlagezustand-VM : Anfahren Fehlerstatus", "Anlagezustand-BM : Anfahren Fehlerstatus"]):
                    duration = (time - current_start_time).total_seconds() / 60
                    if duration >= 30:  # Only include intervals of at least 30 minutes
                        self.add_interval(current_start_time, time, 'green')
                    current_start_time = None

            # Plot all intervals
            for start, duration, color in self.process_intervals:
                self.ax.broken_barh([(start, duration)], (0, block_height), facecolors=(color), alpha=1.0)

            # Plot error and warning bars on top of the green blocks
            for start, duration, color in self.process_intervals:
                interval_data = data[(data['TimeString'] >= start) & (data['TimeString'] <= (start + duration))]
                for index, row in interval_data.iterrows():
                    time = pd.to_datetime(row['TimeString'])
                    msg_number = row['MsgNumber']
                    state_after = row['StateAfter']
                    if msg_number in warning_msg_numbers and state_after == 1:  # Warning with StateAfter 1
                        self.ax.vlines(x=time, ymin=0, ymax=block_height, colors='orange', alpha=1.0)
                    elif msg_number <= 175 and state_after == 1:  # Error with StateAfter 1
                        self.ax.vlines(x=time, ymin=0, ymax=block_height, colors='red', alpha=1.0)
        else:
            color_sequence = [
                (["Anlagezustand-BM : Quelle einrichten"], ["Anlagezustand-BM : Belüften", "Anlagezustand-VM : Belüften", "Anlagezustand-BM : Abpumpen", "Anlagezustand-VM : Abpumpen", "Anlagezustand-BM : Prozess starten"], 'purple'),
                (["Anlagezustand-BM : Belüften", "Anlagezustand-VM : Belüften"], ["Anlagezustand-BM : Quelle einrichten", "Anlagezustand-BM : Abpumpen", "Anlagezustand-VM : Abpumpen", "Anlagezustand-BM : Prozess starten"], 'cyan'),
                (["Anlagezustand-BM : Abpumpen", "Anlagezustand-VM : Abpumpen"], ["Anlagezustand-BM : Quelle einrichten", "Anlagezustand-BM : Belüften", "Anlagezustand-VM : Belüften", "Anlagezustand-BM : Prozess starten"], 'blue'),
                (["Anlagezustand-BM : Prozess starten"], ["Anlagezustand-BM : Prozess beenden", "Anlagezustand-VM : Anfahren Fehlerstatus", "Anlagezustand-BM : Anfahren Fehlerstatus"], 'green')
            ]

            for start_processes, end_processes, color in color_sequence:
                current_start_time = None
                for index, row in data.iterrows():
                    msg_text = row['MsgText']
                    time = pd.to_datetime(row['TimeString'])
                    if any(start_process in msg_text for start_process in start_processes):
                        current_start_time = time
                    if current_start_time is not None and any(end_process in msg_text for end_process in end_processes):
                        duration = (time - current_start_time).total_seconds() / 60
                        if color == 'green' and duration >= 30:  # Only include green intervals of at least 30 minutes
                            self.add_interval(current_start_time, time, color)
                        elif color != 'green':
                            self.add_interval(current_start_time, time, color)
                        current_start_time = None

                # Add the last interval if it exists
                if current_start_time is not None:
                    duration = (end_time - current_start_time).total_seconds() / 60
                    if color == 'green' and duration >= 30:  # Only include green intervals of at least 30 minutes
                        self.add_interval(current_start_time, end_time, color)
                    elif color != 'green':
                        self.add_interval(current_start_time, end_time, color)

            # Plot all intervals
            for start, duration, color in self.process_intervals:
                self.ax.broken_barh([(start, duration)], (0, block_height), facecolors=(color), alpha=1.0)

            # Plot error and warning bars on top of the colored blocks
            for index, row in data.iterrows():
                time = pd.to_datetime(row['TimeString'])
                msg_number = row['MsgNumber']
                state_after = row['StateAfter']
                if msg_number in warning_msg_numbers and state_after == 1:  # Warning with StateAfter 1
                    self.ax.vlines(x=time, ymin=0, ymax=block_height, colors='orange', alpha=1.0)
                elif msg_number <= 175 and state_after == 1:  # Error with StateAfter 1
                    self.ax.vlines(x=time, ymin=0, ymax=block_height, colors='red', alpha=1.0)

        # Adjust axes
        self.ax.set_ylim(0, block_height)
        
        if day_view:
            self.ax.set_xlim(start_time, end_time)
            self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
            self.ax.set_xticks([start_time + pd.Timedelta(hours=i) for i in range(25)])
            self.ax.set_xticklabels([str(i) for i in range(24)] + ['24'])
            self.ax.set_xlabel('Hour')
        else:
            self.ax.set_xlim(data['TimeString'].min(), data['TimeString'].max())
            self.ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            plt.setp(self.ax.get_xticklabels(), rotation=45, ha="right")
            self.ax.set_xlabel('')

        self.ax.set_yticks([])
        self.ax.grid(False)
        
        # Add legend
        legend_elements = [
            Patch(facecolor='cyan', edgecolor='black', label='Ventilation'),
            Patch(facecolor='blue', edgecolor='black', label='Pump out'),
            Patch(facecolor='purple', edgecolor='black', label='Set up'),
            Patch(facecolor='green', edgecolor='black', label='Coating'),
            Patch(facecolor='orange', edgecolor='black', label='Warning', alpha=1.0),
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
                error_data = self.data[(self.data['MsgNumber'] <= 175) & (self.data['StateAfter'] == 1)]
                error_counts = error_data['MsgText'].value_counts().reset_index()
                error_counts.columns = ['Error Message', 'Count']

                self.table.setRowCount(len(error_counts))
                self.table.setColumnCount(2)
                self.table.setHorizontalHeaderLabels(['Error Message', 'Count'])

                for row in range(len(error_counts)):
                    self.table.setItem(row, 0, QTableWidgetItem(error_counts.iloc[row, 0]))
                    self.table.setItem(row, 1, QTableWidgetItem(str(error_counts.iloc[row, 1])))

            elif self.table_type == 'chronology':
                error_data = self.data[(self.data['MsgNumber'] <= 175) & (self.data['StateAfter'] == 1)].sort_values(by='TimeString')
                self.table.setRowCount(len(error_data))
                self.table.setColumnCount(2)
                self.table.setHorizontalHeaderLabels(['Time', 'Error Message'])

                for row in range(len(error_data)):
                    self.table.setItem(row, 0, QTableWidgetItem(error_data.iloc[row]['TimeString'].strftime('%d.%m.%Y %H:%M:%S')))
                    self.table.setItem(row, 1, QTableWidgetItem(error_data.iloc[row]['MsgText']))

            elif self.table_type == 'fail':
                error_data = self.get_fail_data()
                error_counts = error_data['MsgText'].value_counts().reset_index()
                error_counts.columns = ['Error Message', 'Count']

                self.table.setRowCount(len(error_counts))
                self.table.setColumnCount(2)
                self.table.setHorizontalHeaderLabels(['Error Message', 'Count'])

                for row in range(len(error_counts)):
                    self.table.setItem(row, 0, QTableWidgetItem(error_counts.iloc[row, 0]))
                    self.table.setItem(row, 1, QTableWidgetItem(str(error_counts.iloc[row, 1])))

                # Calculate and add percentage row
                excluded_msg_numbers = list(range(29, 38)) + list(range(58, 66)) + list(range(73, 80)) + list(range(90, 93)) + list(range(125, 141)) + list(range(148, 152)) + [173, 174]
                total_errors = len(self.data[(self.data['MsgNumber'] <= 175) & (~self.data['MsgNumber'].isin(excluded_msg_numbers)) & (self.data['StateAfter'] == 1)])
                fail_errors = len(error_data)
                percentage = (fail_errors / total_errors) * 100 if total_errors > 0 else 0

                self.table.insertRow(self.table.rowCount())
                self.table.setItem(self.table.rowCount()-1, 0, QTableWidgetItem("Percentage of Fail Errors"))
                self.table.setItem(self.table.rowCount()-1, 1, QTableWidgetItem(f"{percentage:.2f}%"))

            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        else:
            self.table.setRowCount(0)
            self.table.setColumnCount(2)
            if self.table_type == 'count':
                self.table.setHorizontalHeaderLabels(['Error Message', 'Count'])
            elif self.table_type == 'chronology':
                self.table.setHorizontalHeaderLabels(['Time', 'Error Message'])
            elif self.table_type == 'fail':
                self.table.setHorizontalHeaderLabels(['Error Message', 'Count'])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def get_fail_data(self):
        excluded_msg_numbers = list(range(29, 38)) + list(range(58, 66)) + list(range(73, 80)) + list(range(90, 93)) + list(range(125, 141)) + list(range(148, 152)) + [173, 174]
        fail_errors = []
        process_start_time = None
        error_messages = ["Anlagezustand-BM : Prozess beenden", "Anlagezustand-VM : Anfahren Fehlerstatus", "Anlagezustand-BM : Anfahren Fehlerstatus"]

        for index, row in self.data.iterrows():
            if "Anlagezustand-BM : Prozess starten" in row['MsgText']:
                process_start_time = row['TimeString']
            if process_start_time is not None and any(error_msg in row['MsgText'] for error_msg in error_messages):
                process_end_time = row['TimeString']
                duration = (process_end_time - process_start_time).total_seconds() / 60
                if duration >= 30:
                    fail_window_start = process_end_time - timedelta(seconds=30)
                    fail_window_end = process_end_time + timedelta(seconds=30)
                    fail_data = self.data[(self.data['TimeString'] >= fail_window_start) &
                                          (self.data['TimeString'] <= fail_window_end) &
                                          (self.data['MsgNumber'] <= 175) &
                                          (self.data['StateAfter'] == 1) &
                                          (~self.data['MsgNumber'].isin(excluded_msg_numbers))]
                    if not fail_data.empty:
                        fail_errors.append(fail_data)
                process_start_time = None
        if fail_errors:
            return pd.concat(fail_errors)
        else:
            return pd.DataFrame(columns=self.data.columns)

    def get_fail_chronology_data(self):
        excluded_msg_numbers = list(range(29, 38)) + list(range(58, 66)) + list(range(73, 80)) + list(range(90, 93)) + list(range(125, 141)) + list(range(148, 152)) + [173, 174]
        fail_chronology_data = []
        process_start_time = None
        error_messages = ["Anlagezustand-BM : Prozess beenden", "Anlagezustand-VM : Anfahren Fehlerstatus", "Anlagezustand-BM : Anfahren Fehlerstatus"]

        for index, row in self.data.iterrows():
            if "Anlagezustand-BM : Prozess starten" in row['MsgText']:
                process_start_time = row['TimeString']
            if process_start_time is not None and any(error_msg in row['MsgText'] for error_msg in error_messages):
                process_end_time = row['TimeString']
                duration = (process_end_time - process_start_time).total_seconds() / 60
                if duration >= 30:
                    fail_window_start = process_end_time - timedelta(seconds=30)
                    fail_window_end = process_end_time + timedelta(seconds=30)
                    fail_data = self.data[(self.data['TimeString'] >= fail_window_start) &
                                          (self.data['TimeString'] <= fail_window_end) &
                                          (self.data['StateAfter'] == 1) &
                                          (~self.data['MsgNumber'].isin(excluded_msg_numbers))]
                    if not fail_data.empty:
                        fail_chronology_data.append(fail_data)
                process_start_time = None
        if fail_chronology_data:
            return pd.concat(fail_chronology_data)
        else:
            return pd.DataFrame(columns=self.data.columns)
        
class ErrorTableDay(QWidget):
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
            if self.table_type == 'fail':
                fail_data = self.get_fail_data_day()
                error_counts = fail_data['MsgText'].value_counts().reset_index()
                error_counts.columns = ['Error Message', 'Count']

                self.table.setRowCount(len(error_counts))
                self.table.setColumnCount(2)
                self.table.setHorizontalHeaderLabels(['Error Message', 'Count'])

                for row in range(len(error_counts)):
                    self.table.setItem(row, 0, QTableWidgetItem(error_counts.iloc[row, 0]))
                    self.table.setItem(row, 1, QTableWidgetItem(str(error_counts.iloc[row, 1])))

                self.table.insertRow(self.table.rowCount())
                self.table.setItem(self.table.rowCount()-1, 0, QTableWidgetItem("Percentage of Fail Errors"))
                self.table.setItem(self.table.rowCount()-1, 1, QTableWidgetItem(f"{self.calculate_percentage_fail(fail_data):.2f}%"))
            elif self.table_type == 'fail_chronology':
                fail_data = self.get_fail_data_day()
                fail_data = fail_data.sort_values(by='TimeString')
                self.table.setRowCount(len(fail_data))
                self.table.setColumnCount(2)
                self.table.setHorizontalHeaderLabels(['Time', 'Error Message'])

                for row in range(len(fail_data)):
                    self.table.setItem(row, 0, QTableWidgetItem(fail_data.iloc[row]['TimeString'].strftime('%d.%m.%Y %H:%M:%S')))
                    self.table.setItem(row, 1, QTableWidgetItem(fail_data.iloc[row]['MsgText']))

            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        else:
            self.table.setRowCount(0)
            self.table.setColumnCount(2)
            if self.table_type == 'count':
                self.table.setHorizontalHeaderLabels(['Error Message', 'Count'])
            elif self.table_type == 'chronology':
                self.table.setHorizontalHeaderLabels(['Time', 'Error Message'])
            elif self.table_type == 'fail':
                self.table.setHorizontalHeaderLabels(['Error Message', 'Count'])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def get_fail_data_day(self):
        excluded_msg_numbers = list(range(29, 38)) + list(range(58, 66)) + list(range(73, 80)) + list(range(90, 93)) + list(range(125, 141)) + list(range(148, 152)) + [173, 174]
        error_messages = ["Anlagezustand-BM : Prozess beenden", "Anlagezustand-VM : Anfahren Fehlerstatus", "Anlagezustand-BM : Anfahren Fehlerstatus"]
        fail_data = []
        for index, row in self.data.iterrows():
            if any(error_msg in row['MsgText'] for error_msg in error_messages):
                error_window_start = row['TimeString'] - timedelta(seconds=30)
                error_window_end = row['TimeString'] + timedelta(seconds=30)
                fail_window_data = self.data[(self.data['TimeString'] >= error_window_start) & 
                                             (self.data['TimeString'] <= error_window_end) & 
                                             (self.data['StateAfter'] == 1) & 
                                             (~self.data['MsgNumber'].isin(excluded_msg_numbers))]
                fail_data.append(fail_window_data[fail_window_data['MsgNumber'] <= 175])
        if fail_data:
            return pd.concat(fail_data)
        else:
            return pd.DataFrame(columns=self.data.columns)

    def calculate_percentage_fail(self, fail_data):
        excluded_msg_numbers = list(range(29, 38)) + list(range(58, 66)) + list(range(73, 80)) + list(range(90, 93)) + list(range(125, 141)) + list(range(148, 152)) + [173, 174]
        total_errors = len(self.data[(self.data['MsgNumber'] <= 175) & (self.data['StateAfter'] == 1) & (~self.data['MsgNumber'].isin(excluded_msg_numbers))])
        fail_errors = len(fail_data)
        return (fail_errors / total_errors) * 100 if total_errors > 0 else 0


class StatisticsTab(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Add the plot
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        # Add the statistics text
        self.statistics_label = QLabel(self)
        self.statistics_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.statistics_label)

        self.setLayout(layout)
        self.update_statistics()

    def update_statistics(self):
        if self.data is not None:
            process_durations = []
            failed_processes = 0
            process_start_time = None
            error_messages = ["Anlagezustand-BM : Prozess beenden", "Anlagezustand-VM : Anfahren Fehlerstatus", "Anlagezustand-BM : Anfahren Fehlerstatus"]

            for index, row in self.data.iterrows():
                if "Anlagezustand-BM : Prozess starten" in row['MsgText']:
                    process_start_time = row['TimeString']
                if any(error_msg in row['MsgText'] for error_msg in error_messages) and process_start_time is not None:
                    process_end_time = row['TimeString']
                    duration = (process_end_time - process_start_time).total_seconds() / 60
                    if duration >= 30:
                        process_durations.append(duration)
                        if self.has_errors_within_window(process_end_time):
                            failed_processes += 1
                    process_start_time = None

            total_processes = len(process_durations)
            percentage_failed = (failed_processes / total_processes) * 100 if total_processes > 0 else 0

            self.ax.clear()
            self.ax.barh(['All', 'Failed'], [total_processes, failed_processes], color=['green', 'red'])
            self.ax.set_xlabel('Amount of Processes')
            self.ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
            self.fig.tight_layout()
            self.canvas.draw()

            self.statistics_label.setText(f"Amount of all processes: {total_processes}\nAmount of failed processes: {failed_processes}\nPercentage of failed processes: {percentage_failed:.2f}%")
        else:
            self.ax.clear()
            self.ax.set_title('No Data')
            self.canvas.draw()
            self.statistics_label.setText("Amount of all processes: 0\nAmount of failed processes: 0\nPercentage of failed processes: 0.00%")

    def has_errors_within_window(self, process_end_time):
        excluded_msg_numbers = list(range(29, 38)) + list(range(58, 66)) + list(range(73, 80)) + list(range(90, 93)) + list(range(125, 141)) + list(range(148, 152)) + [173, 174]
        error_window_start = process_end_time - timedelta(seconds=30)
        error_window_end = process_end_time + timedelta(seconds=30)
        error_data = self.data[(self.data['TimeString'] >= error_window_start) &
                               (self.data['TimeString'] <= error_window_end) &
                               (self.data['MsgNumber'] <= 175) &
                               (self.data['StateAfter'] == 1) &
                               (~self.data['MsgNumber'].isin(excluded_msg_numbers))]
        return not error_data.empty

class LoadingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error Reporter")
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        self.setFixedSize(300, 100)
        layout = QVBoxLayout(self)
        self.label = QLabel("Loading data...", self)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(pd.DataFrame)
    progress_updated = pyqtSignal(int)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        chunk_size = 1000
        total_rows = sum(1 for _ in open(self.file_path, 'r', encoding='latin1')) - 1
        chunks = []
        for chunk in pd.read_csv(self.file_path, delimiter=';', encoding='latin1', chunksize=chunk_size, on_bad_lines='skip'):
            chunks.append(chunk)
            self.progress_updated.emit(int(len(chunks) * chunk_size / total_rows * 100))
        data = pd.concat(chunks, ignore_index=True)
        self.data_loaded.emit(data)

class MultipleDataLoaderThread(QThread):
    common_errors_found = pyqtSignal(pd.DataFrame)
    progress_updated = pyqtSignal(int)

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        dataframes = []
        total_files = len(self.file_paths)
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {executor.submit(self.load_file, file): file for file in self.file_paths}
            for i, future in enumerate(as_completed(future_to_file)):
                df = future.result()
                dataframes.append(df)
                self.progress_updated.emit(int((i + 1) / total_files * 100))
        
        common_errors = self.find_common_errors(dataframes)
        self.common_errors_found.emit(common_errors)

    def load_file(self, file):
        dtype = {
            'TimeString': 'str',
            'MsgNumber': 'int32',
            'MsgText': 'str',
            'StateAfter': 'int32'
        }
        df = pd.read_csv(file, delimiter=';', encoding='latin1', dtype=dtype, on_bad_lines='skip')
        df['TimeString'] = pd.to_datetime(df['TimeString'].apply(self.correct_time_format))
        return df

    def correct_time_format(self, time_str):
        try:
            return datetime.strptime(time_str, '%d.%m.%Y %H:%M:%S')
        except ValueError:
            return datetime.strptime(time_str, '%d.%m.%Y %H:%M').replace(second=0)

    def find_common_errors(self, dataframes):
        common_errors = pd.DataFrame(columns=['Date', 'Error Message', 'Count'])

        for date in pd.to_datetime(dataframes[0]['TimeString']).dt.date.unique():
            errors = []
            for df in dataframes:
                df_on_date = df[pd.to_datetime(df['TimeString']).dt.date == date]
                errors.append(df_on_date[(df_on_date['MsgNumber'] <= 175) & (df_on_date['StateAfter'] == 1)]['MsgText'].value_counts())

            common = errors[0]
            for err in errors[1:]:
                common = common.combine(err, min, fill_value=0)

            for error, count in common[common > 0].items():
                common_errors = pd.concat([common_errors, pd.DataFrame([{'Date': date, 'Error Message': error, 'Count': count}])], ignore_index=True)

        return common_errors

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
        self.tab_info = QWidget()

        self.main_tabs.addTab(self.tab_single, "Single")
        self.main_tabs.addTab(self.tab_multiple, "Multiple")
        self.main_tabs.addTab(self.tab_info, "Info")

        self.init_single_tab()
        self.init_multiple_tab()
        self.init_info_tab()

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

        self.buttons = ["ISD1A", "DECK1A", "SEED1A", "SL1A", "SL1B", "AG1A", "OX1A"]
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

        self.loading_dialog = LoadingDialog(self)
        self.loading_dialog.show()

        self.loader_thread = MultipleDataLoaderThread(selected_files.values())
        self.loader_thread.progress_updated.connect(self.loading_dialog.progress_bar.setValue)
        self.loader_thread.common_errors_found.connect(lambda common_errors: self.display_common_errors(common_errors, " ".join(selected_files.keys()) + " Common Errors"))
        self.loader_thread.finished.connect(self.loading_dialog.close)
        self.loader_thread.start()

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
        self.day_chronology_tab = QWidget()
        self.day_count_tab = QWidget()
        self.day_fail_chronology_tab = QWidget()
        self.day_fail_count_tab = QWidget()

        self.day_tabs.addTab(self.day_chronology_tab, "Chronology")
        self.day_tabs.addTab(self.day_count_tab, "Count")
        self.day_tabs.addTab(self.day_fail_chronology_tab, "Error Chronology")
        self.day_tabs.addTab(self.day_fail_count_tab, "Error Count")

        self.day_chronology_all_layout = QVBoxLayout(self.day_chronology_tab)
        self.day_count_all_layout = QVBoxLayout(self.day_count_tab)
        self.day_fail_chronology_layout = QVBoxLayout(self.day_fail_chronology_tab)
        self.day_fail_count_layout = QVBoxLayout(self.day_fail_count_tab)

        self.error_table_day_chronology_all = ErrorTable(None, self.day_chronology_tab, table_type='chronology')
        self.error_table_day_count_all = ErrorTable(None, self.day_count_tab)
        self.error_table_day_fail_chronology = ErrorTable(None, self.day_fail_chronology_tab, table_type='chronology')
        self.error_table_day_fail_count = ErrorTable(None, self.day_fail_count_tab, table_type='fail')

        self.day_chronology_all_layout.addWidget(self.error_table_day_chronology_all)
        self.day_count_all_layout.addWidget(self.error_table_day_count_all)
        self.day_fail_chronology_layout.addWidget(self.error_table_day_fail_chronology)
        self.day_fail_count_layout.addWidget(self.error_table_day_fail_count)

        layout.addWidget(self.day_tabs)

    def init_all_tab(self):
        layout = QVBoxLayout(self.tab_all)
        self.canvas_all = BlockDiagramCanvas(self.tab_all)
        layout.addWidget(self.canvas_all)

        self.all_tabs = QTabWidget()
        self.all_chronology_tab = QWidget()
        self.all_count_tab = QWidget()
        self.all_fail_chronology_tab = QWidget()
        self.all_fail_count_tab = QWidget()
        self.statistics_tab = QWidget()

        self.all_tabs.addTab(self.all_chronology_tab, "Chronology")
        self.all_tabs.addTab(self.all_count_tab, "Count")
        self.all_tabs.addTab(self.all_fail_chronology_tab, "Fail Chronology")
        self.all_tabs.addTab(self.all_fail_count_tab, "Fail Count")
        self.all_tabs.addTab(self.statistics_tab, "Statistics")

        self.all_chronology_all_layout = QVBoxLayout(self.all_chronology_tab)
        self.all_count_all_layout = QVBoxLayout(self.all_count_tab)
        self.all_fail_chronology_layout = QVBoxLayout(self.all_fail_chronology_tab)
        self.all_fail_count_layout = QVBoxLayout(self.all_fail_count_tab)

        self.error_table_all_chronology_all = ErrorTable(None, self.all_chronology_tab, table_type='chronology')
        self.error_table_all_count_all = ErrorTable(None, self.all_count_tab)
        self.error_table_all_fail_chronology = ErrorTable(None, self.all_fail_chronology_tab, table_type='chronology')
        self.error_table_all_fail_count = ErrorTable(None, self.all_fail_count_tab, table_type='fail')

        self.all_chronology_all_layout.addWidget(self.error_table_all_chronology_all)
        self.all_count_all_layout.addWidget(self.error_table_all_count_all)
        self.all_fail_chronology_layout.addWidget(self.error_table_all_fail_chronology)
        self.all_fail_count_layout.addWidget(self.error_table_all_fail_count)

        self.statistics_widget = StatisticsTab(self.data, self.statistics_tab)
        self.statistics_layout = QVBoxLayout(self.statistics_tab)
        self.statistics_layout.addWidget(self.statistics_widget)

        layout.addWidget(self.all_tabs)

    def init_info_tab(self):
        layout = QVBoxLayout(self.tab_info)
        info_label = QLabel(self.tab_info)
        info_label.setFont(QFont("Arial", 14))
        info_label.setText(
            "◯ In 'Single' tab one imports CSV file of each machine.\n"
            "◯ In 'Multiple' tab one compares different errors per day in different machines.\n"
            "◯ All errors are shown in 'Chronology' and 'Count' tabs, but errors which led to process failure in 'Fail Chronology' and 'Fail Count'.\n"
            "◯ Failure errors are within 30 seconds before and after the spontaneous end of coating process.\n"
            "◯'Percentage of Fail Errors' reflects the portion of failure errors to all errors.\n"
            "◯ In 'All' tab the processes are at least 30 min long."
        )
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.reset_state()  # Reset state before loading new file

            self.loading_dialog = LoadingDialog(self)
            self.loading_dialog.show()

            self.loader_thread = DataLoaderThread(file_path)
            self.loader_thread.progress_updated.connect(self.loading_dialog.progress_bar.setValue)
            self.loader_thread.data_loaded.connect(self.on_data_loaded)
            self.loader_thread.start()

    def reset_state(self):
        # Clear existing data and reset relevant variables
        self.data = None
        self.date_dropdown.clear()
        self.tabs.hide()
        self.canvas_day.process_intervals.clear()
        self.canvas_all.process_intervals.clear()
        
        self.error_table_day_chronology_all.data = None
        self.error_table_day_chronology_all.populate_table()
        self.error_table_day_count_all.data = None
        self.error_table_day_count_all.populate_table()
        self.error_table_day_fail_chronology.data = None
        self.error_table_day_fail_chronology.populate_table()
        self.error_table_day_fail_count.data = None
        self.error_table_day_fail_count.populate_table()
        
        self.error_table_all_chronology_all.data = None
        self.error_table_all_chronology_all.populate_table()
        self.error_table_all_count_all.data = None
        self.error_table_all_count_all.populate_table()
        self.error_table_all_fail_chronology.data = None
        self.error_table_all_fail_chronology.populate_table()
        self.error_table_all_fail_count.data = None
        self.error_table_all_fail_count.populate_table()
        
        self.statistics_widget.data = None
        self.statistics_widget.update_statistics()

    def on_data_loaded(self, data):
        self.data = data
        self.process_data()
        self.populate_dates()
        self.update_all_tab()
        self.update_day_tab()
        self.tabs.show()  # Show tabs after successful import
        self.loading_dialog.close()

    def process_data(self):
        try:
            self.data['TimeString'] = self.data['TimeString'].apply(self.correct_time_format)
            self.data['TimeString'] = pd.to_datetime(self.data['TimeString'])
        except Exception as e:
            print(f"Error processing data: {e}")

    def correct_time_format(self, time_str):
        try:
            return datetime.strptime(time_str, '%d.%m.%Y %H:%M:%S')
        except ValueError:
            return datetime.strptime(time_str, '%d.%m.%Y %H:%M').replace(second=0)

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
            self.canvas_day.plot(self.data, start_time, end_time, day_view=True)
            self.update_error_tables_day(start_time, end_time)

    def update_error_tables_day(self, start_time, end_time):
        day_data = self.data[(self.data['TimeString'] >= start_time) & (self.data['TimeString'] <= end_time)]
        self.error_table_day_chronology_all.data = day_data
        self.error_table_day_chronology_all.populate_table()
        self.error_table_day_count_all.data = day_data
        self.error_table_day_count_all.populate_table()
        self.error_table_day_fail_chronology.data = day_data
        self.error_table_day_fail_chronology.populate_table()
        self.error_table_day_fail_count.data = day_data
        self.error_table_day_fail_count.populate_table()

    def update_error_tables(self, start_time, end_time):
        day_data = self.data[(self.data['TimeString'] >= start_time) & (self.data['TimeString'] <= end_time)]
        self.error_table_day_chronology_all.data = day_data
        self.error_table_day_chronology_all.populate_table()
        self.error_table_day_count_all.data = day_data
        self.error_table_day_count_all.populate_table()
        self.error_table_day_fail_chronology.data = self.get_fail_chronology_data(day_data)
        self.error_table_day_fail_chronology.populate_table()
        self.error_table_day_fail_count.data = day_data
        self.error_table_day_fail_count.populate_table()

    def update_all_tab(self):
        if self.data is not None:
            start_time = self.data['TimeString'].min().normalize()
            end_time = self.data['TimeString'].max().normalize() + pd.Timedelta(days=1)
            self.canvas_all.plot(self.data, start_time, end_time, day_view=False, plot_coating_only=True)
            self.error_table_all_chronology_all.data = self.data
            self.error_table_all_chronology_all.populate_table()
            self.error_table_all_count_all.data = self.data
            self.error_table_all_count_all.populate_table()
            self.error_table_all_fail_chronology.data = self.get_fail_chronology_data(self.data)
            self.error_table_all_fail_chronology.populate_table()
            self.error_table_all_fail_count.data = self.data
            self.error_table_all_fail_count.populate_table()
            self.statistics_widget.data = self.data
            self.statistics_widget.update_statistics()

    def get_fail_chronology_data(self, data):
        excluded_msg_numbers = list(range(29, 38)) + list(range(58, 66)) + list(range(73, 80)) + list(range(90, 93)) + list(range(125, 141)) + list(range(148, 152)) + [173, 174]
        fail_chronology_data = []
        process_start_time = None
        error_messages = ["Anlagezustand-BM : Prozess beenden", "Anlagezustand-VM : Anfahren Fehlerstatus", "Anlagezustand-BM : Anfahren Fehlerstatus"]

        for index, row in data.iterrows():
            if "Anlagezustand-BM : Prozess starten" in row['MsgText']:
                process_start_time = row['TimeString']
            if process_start_time is not None and any(error_msg in row['MsgText'] for error_msg in error_messages):
                process_end_time = row['TimeString']
                duration = (process_end_time - process_start_time).total_seconds() / 60
                if duration >= 30:
                    fail_window_start = process_end_time - timedelta(seconds=30)
                    fail_window_end = process_end_time + timedelta(seconds=30)
                    fail_data = self.data[(data['TimeString'] >= fail_window_start) &
                                          (data['TimeString'] <= fail_window_end) &
                                          (data['StateAfter'] == 1) &
                                          (~data['MsgNumber'].isin(excluded_msg_numbers))]
                    if not fail_data.empty:
                        fail_chronology_data.append(fail_data)
                process_start_time = None
        if fail_chronology_data:
            return pd.concat(fail_chronology_data)
        else:
            return pd.DataFrame(columns=self.data.columns)
        
    def init_day_tab(self):
        layout = QVBoxLayout(self.tab_day)
        self.date_dropdown = QComboBox()
        self.date_dropdown.currentIndexChanged.connect(self.update_day_tab)
        layout.addWidget(self.date_dropdown)
        self.canvas_day = BlockDiagramCanvas(self.tab_day)
        layout.addWidget(self.canvas_day)

        self.day_tabs = QTabWidget()
        self.day_chronology_tab = QWidget()
        self.day_count_tab = QWidget()
        self.day_fail_chronology_tab = QWidget()
        self.day_fail_count_tab = QWidget()

        self.day_tabs.addTab(self.day_chronology_tab, "Chronology")
        self.day_tabs.addTab(self.day_count_tab, "Count")
        self.day_tabs.addTab(self.day_fail_chronology_tab, "Error Chronology")
        self.day_tabs.addTab(self.day_fail_count_tab, "Error Count")

        self.day_chronology_all_layout = QVBoxLayout(self.day_chronology_tab)
        self.day_count_all_layout = QVBoxLayout(self.day_count_tab)
        self.day_fail_chronology_layout = QVBoxLayout(self.day_fail_chronology_tab)
        self.day_fail_count_layout = QVBoxLayout(self.day_fail_count_tab)

        self.error_table_day_chronology_all = ErrorTable(None, self.day_chronology_tab, table_type='chronology')
        self.error_table_day_count_all = ErrorTable(None, self.day_count_tab)
        self.error_table_day_fail_chronology = ErrorTableDay(None, self.day_fail_chronology_tab, table_type='fail_chronology')
        self.error_table_day_fail_count = ErrorTableDay(None, self.day_fail_count_tab, table_type='fail')

        self.day_chronology_all_layout.addWidget(self.error_table_day_chronology_all)
        self.day_count_all_layout.addWidget(self.error_table_day_count_all)
        self.day_fail_chronology_layout.addWidget(self.error_table_day_fail_chronology)
        self.day_fail_count_layout.addWidget(self.error_table_day_fail_count)

        layout.addWidget(self.day_tabs)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.showMaximized()
    sys.exit(app.exec_())