-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.consultations (
  doctor_id uuid NOT NULL,
  patient_id uuid NOT NULL,
  pradhi_submission_id character varying UNIQUE,
  parent_consultation_id uuid,
  raw_pradhi_response jsonb,
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  consultation_time timestamp with time zone NOT NULL DEFAULT (now() AT TIME ZONE 'Asia/Kolkata'::text),
  transcription_status character varying DEFAULT 'pending'::character varying,
  webhook_received_at timestamp with time zone,
  CONSTRAINT consultations_pkey PRIMARY KEY (id),
  CONSTRAINT consultations_parent_consultation_id_fkey FOREIGN KEY (parent_consultation_id) REFERENCES public.consultations(id),
  CONSTRAINT consultations_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id),
  CONSTRAINT consultations_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id)
);
CREATE TABLE public.dispatch_segments (
  dispatch_id uuid NOT NULL,
  segment_id uuid NOT NULL,
  CONSTRAINT dispatch_segments_pkey PRIMARY KEY (dispatch_id, segment_id),
  CONSTRAINT dispatch_segments_dispatch_id_fkey FOREIGN KEY (dispatch_id) REFERENCES public.dispatches(id),
  CONSTRAINT dispatch_segments_segment_id_fkey FOREIGN KEY (segment_id) REFERENCES public.record_segments(id)
);
CREATE TABLE public.dispatches (
  consultation_id uuid NOT NULL,
  dispatched_by_id uuid NOT NULL,
  dispatch_method character varying NOT NULL,
  s3_pdf_url text,
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  sent_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT dispatches_pkey PRIMARY KEY (id),
  CONSTRAINT dispatches_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id)
);
CREATE TABLE public.doctor_patient_assignments (
  doctor_id uuid NOT NULL,
  patient_id uuid NOT NULL,
  protocol_score integer,
  adherence_score integer,
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  CONSTRAINT doctor_patient_assignments_pkey PRIMARY KEY (id),
  CONSTRAINT doctor_patient_assignments_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id),
  CONSTRAINT doctor_patient_assignments_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id)
);
CREATE TABLE public.doctor_patient_relations (
  doctor_id uuid NOT NULL,
  patient_id uuid NOT NULL,
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  is_active boolean DEFAULT true,
  CONSTRAINT doctor_patient_relations_pkey PRIMARY KEY (id),
  CONSTRAINT doctor_patient_relations_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id),
  CONSTRAINT doctor_patient_relations_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(id)
);
CREATE TABLE public.doctor_settings (
  hospital_pharmacy_whatsapp character varying,
  doctor_id uuid NOT NULL,
  default_dispatch_sections jsonb,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT doctor_settings_pkey PRIMARY KEY (doctor_id),
  CONSTRAINT doctor_settings_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id)
);
CREATE TABLE public.doctors (
  onehat_doctor_id bigint NOT NULL UNIQUE,
  hospital_id bigint NOT NULL,
  username character varying NOT NULL UNIQUE,
  full_name text,
  email character varying UNIQUE,
  specialty character varying,
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT doctors_pkey PRIMARY KEY (id),
  CONSTRAINT doctors_hospital_id_fkey FOREIGN KEY (hospital_id) REFERENCES public.hospitals(id)
);
CREATE TABLE public.hospitals (
  id bigint NOT NULL,
  name text NOT NULL,
  CONSTRAINT hospitals_pkey PRIMARY KEY (id)
);
CREATE TABLE public.nurses (
  doctor_id uuid NOT NULL,
  username character varying NOT NULL UNIQUE,
  full_name text,
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  CONSTRAINT nurses_pkey PRIMARY KEY (id),
  CONSTRAINT nurses_doctor_id_fkey FOREIGN KEY (doctor_id) REFERENCES public.doctors(id)
);
CREATE TABLE public.patients (
  gender character varying,
  date_of_birth character varying,
  age integer,
  onehat_patient_id bigint NOT NULL UNIQUE,
  full_name text NOT NULL,
  phone_number character varying,
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  CONSTRAINT patients_pkey PRIMARY KEY (id)
);
CREATE TABLE public.pre_screening_records (
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  patient_uuid uuid,
  patient_onehat_id bigint,
  patient_chosen_doctor_onehat_id bigint,
  suggested_department character varying,
  suggested_doctor_onehat_id bigint,
  visit_type character varying,
  investigative_history text,
  possible_diagnosis text,
  chief_complaint text,
  symptoms_mentioned ARRAY,
  diagnostics jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT pre_screening_records_pkey PRIMARY KEY (id),
  CONSTRAINT pre_screening_records_patient_uuid_fkey FOREIGN KEY (patient_uuid) REFERENCES public.patients(id)
);
CREATE TABLE public.record_segments (
  consultation_id uuid NOT NULL,
  segment_type character varying NOT NULL,
  original_content text,
  edited_content text,
  id uuid NOT NULL DEFAULT uuid_generate_v4(),
  is_verified boolean NOT NULL DEFAULT false,
  edit_count integer NOT NULL DEFAULT 0,
  sent_count integer NOT NULL DEFAULT 0,
  CONSTRAINT record_segments_pkey PRIMARY KEY (id),
  CONSTRAINT record_segments_consultation_id_fkey FOREIGN KEY (consultation_id) REFERENCES public.consultations(id)
);