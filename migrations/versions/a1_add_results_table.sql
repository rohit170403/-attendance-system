-- Results table schema (raw SQL)
CREATE TABLE IF NOT EXISTS result (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subject(id) ON DELETE CASCADE,
    exam_type VARCHAR(50) NOT NULL,
    marks_obtained DOUBLE PRECISION NOT NULL,
    max_marks DOUBLE PRECISION NOT NULL,
    remarks TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Ensure one row per (student, subject, exam_type)
CREATE UNIQUE INDEX IF NOT EXISTS unique_result_per_exam ON result (student_id, subject_id, exam_type);


