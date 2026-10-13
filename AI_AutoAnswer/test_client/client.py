import random
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLabel,
                               QMainWindow, QPushButton, QRadioButton, QVBoxLayout, QWidget)


class PracticeClient(QMainWindow):
    def __init__(self, start_index: int = 0):
        super().__init__()
        self.setWindowTitle("AI AutoAnswer 模拟练习客户端")
        self.resize(800, 600)
        self.index = start_index
        self.total = 30
        self.loading_failure = False
        self._build()
        self.show_question()

    def _build(self):
        main = QWidget(); self.setCentralWidget(main)
        self.layout = QVBoxLayout(main)
        self.heading = QLabel(); self.heading.setWordWrap(True)
        self.heading.setObjectName("question")
        self.layout.addWidget(self.heading)
        self.image = QLabel(); self.layout.addWidget(self.image)
        self.options_box = QVBoxLayout(); self.layout.addLayout(self.options_box)
        self.feedback = QLabel(); self.layout.addWidget(self.feedback)
        row = QHBoxLayout()
        self.next_button = QPushButton("下一题")
        self.next_button.clicked.connect(self.next_question)
        row.addWidget(self.next_button)
        self.failure_button = QCheckBox("模拟下一题加载失败")
        row.addWidget(self.failure_button)
        self.layout.addLayout(row)
        self.layout.addStretch()
        self.setStyleSheet("""QWidget{background:#f8fafc;color:#0f172a;font-size:18px}
            QLabel#question{font-weight:bold;font-size:22px;margin:18px}
            QRadioButton,QCheckBox{padding:12px;border:1px solid #cbd5e1;border-radius:8px}
            QPushButton{background:#2563eb;color:white;padding:12px;border-radius:8px}""")

    def _clear_options(self):
        while self.options_box.count():
            item = self.options_box.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def show_question(self):
        if self.index >= self.total:
            self._clear_options()
            self.heading.setText("全部完成：30 道模拟题已处理")
            self.image.clear()
            self.next_button.hide()
            self.feedback.setText("练习结束，无需最终提交")
            return
        self._clear_options()
        multiple = self.index >= 20
        self.heading.setText(
            f"模拟练习 第 {self.index + 1} 题 / {self.total}："
            + ("多选题。以下哪些属于 Python 内置容器？" if multiple else
               f"单选题。第 {self.index + 1} 组中，哪个结构符合先进先出？")
            + ("请结合图示及定义判断，并注意选项可能改变顺序。" if self.index % 3 == 2 else ""))
        if self.index % 4 == 3:
            pixmap = QPixmap(220, 70); pixmap.fill(QColor("#dbeafe"))
            painter = QPainter(pixmap); painter.drawText(20, 42, "FIFO →")
            painter.end(); self.image.setPixmap(pixmap)
        else:
            self.image.clear()
        texts = {"A": "列表" if multiple else "栈",
                 "B": "元组" if multiple else "队列",
                 "C": "字典" if multiple else "树",
                 "D": "整数" if multiple else "图"}
        if self.index % 4 == 0:
            texts.update({"E": "集合" if multiple else "链表",
                          "F": "浮点数" if multiple else "数组"})
        self.option_buttons = {}
        labels = list(texts)
        random.Random(self.index).shuffle(labels)
        for label in labels:
            cls = QCheckBox if multiple else QRadioButton
            button = cls(f"{label}. {texts[label]}")
            button.toggled.connect(self._update_feedback)
            self.options_box.addWidget(button)
            self.option_buttons[label] = button
        self.feedback.setText("请选择答案")

    def _update_feedback(self):
        multiple = self.index >= 20
        chosen = {label for label, button in self.option_buttons.items() if button.isChecked()}
        expected = {"A", "C"} | ({"E"} if "E" in self.option_buttons else set()) if multiple else {"B"}
        self.feedback.setText("已选择：" + ",".join(sorted(chosen)) +
                              ("（正确）" if chosen == expected else ""))

    def next_question(self):
        if self.failure_button.isChecked():
            self.feedback.setText("模拟加载失败：页面未变化")
            return
        self.heading.setText("加载中…")
        self.next_button.setEnabled(False)
        QTimer.singleShot(350 + (self.index % 3) * 300, self._complete_next)

    def _complete_next(self):
        self.index += 1
        self.next_button.setEnabled(True)
        self.show_question()


def main():
    app = QApplication(sys.argv)
    window = PracticeClient()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
