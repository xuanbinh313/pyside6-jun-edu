from models.database import get_session
from models.exam import ExamSrtChunk

class ExamTranscriptViewModel:
    def __init__(self, exam=None):
        self.exam = exam
        self.srt_chunks = []

    def load_chunks(self, chunks):
        self.srt_chunks = chunks

    def duplicate_chunk(self, chunk):
        list_idx = self.srt_chunks.index(chunk)
        max_idx = max((c.index for c in self.srt_chunks), default=0)
        
        new_chunk = ExamSrtChunk(
            exam_id=chunk.exam_id,
            index=max_idx + 1,
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            text=chunk.text
        )
        self.srt_chunks.insert(list_idx + 1, new_chunk)
        return list_idx + 1, new_chunk

    def merge_chunk(self, chunk):
        list_idx = self.srt_chunks.index(chunk)
        if list_idx >= len(self.srt_chunks) - 1:
            return None, None
            
        next_chunk = self.srt_chunks[list_idx + 1]
        
        chunk.text = f"{chunk.text} {next_chunk.text}"
        chunk.end_time = next_chunk.end_time
        
        self.srt_chunks.pop(list_idx + 1)
        return list_idx, next_chunk

    def save_chunks(self):
        """Persist all current srt_chunks to SQLite, replacing previous ones for this exam."""
        if not self.exam or not self.exam.id:
            return
        
        session = get_session()
        try:
            # Delete all existing chunks for this exam
            session.query(ExamSrtChunk).filter(
                ExamSrtChunk.exam_id == self.exam.id
            ).delete()
            
            # Re-insert all current chunks
            for chunk in self.srt_chunks:
                new_chunk = ExamSrtChunk(
                    exam_id=self.exam.id,
                    index=chunk.index,
                    start_time=chunk.start_time,
                    end_time=chunk.end_time,
                    text=chunk.text,
                    hint=getattr(chunk, 'hint', None),
                )
                session.add(new_chunk)
            
            session.commit()
        finally:
            session.close()

