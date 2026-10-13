"""Conservative exercise-page gate for the user-selected Chaoxing client."""
import re

from app.recognition.models import ObservedQuestion


RESTRICTED = re.compile(r"考试|监考|交卷|正式作业|计分|测验提交|人脸识别|验证码")
PRACTICE = re.compile(r"练习|模拟|自测|题库")


class ChaoxingAdapter:
    @staticmethod
    def applies(process_name: str, title: str) -> bool:
        value = (process_name + " " + title).lower()
        return "cxstudy" in value or "chaoxing" in value or "学习通" in value

    def assert_allowed(self, observed: ObservedQuestion, context: str = "") -> None:
        if observed.finished:
            return
        text = observed.question
        if RESTRICTED.search(text + "\n" + context):
            raise RuntimeError("学习通页面可能属于计分作业或考试；已暂停自动选择")
        if not PRACTICE.search(text):
            raise RuntimeError("无法确认学习通当前为允许自动化的练习页面；已暂停")
