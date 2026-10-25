from app.schemas.common import CamelModel, ChatThreadOut, MessageOut


class ThreadsResponse(CamelModel):
    threads: list[ChatThreadOut]


class CreateThreadRequest(CamelModel):
    course_id: str
    assignment_id: str | None = None
    title: str | None = None


class ThreadResponse(CamelModel):
    thread: ChatThreadOut


class ThreadDetailResponse(CamelModel):
    thread: ChatThreadOut
    messages: list[MessageOut]


class SendMessageResponse(CamelModel):
    sent_message: MessageOut
    reply: MessageOut
