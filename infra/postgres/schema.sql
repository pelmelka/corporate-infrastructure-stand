--
-- PostgreSQL database dump
--


-- Dumped from database version 17.9 (Debian 17.9-0+deb13u1)
-- Dumped by pg_dump version 17.9 (Debian 17.9-0+deb13u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ticket_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ticket_events (
    id bigint NOT NULL,
    ticket_id bigint,
    event text NOT NULL,
    old_status text,
    new_status text,
    source text DEFAULT 'unknown'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    metadata_json jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: ticket_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ticket_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ticket_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ticket_events_id_seq OWNED BY public.ticket_events.id;


--
-- Name: tickets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tickets (
    id bigint NOT NULL,
    schema_version integer DEFAULT 2 NOT NULL,
    title text NOT NULL,
    category text NOT NULL,
    category_label text NOT NULL,
    resource text NOT NULL,
    resource_label text NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    priority text NOT NULL,
    status text NOT NULL,
    source text DEFAULT 'unknown'::text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    resolved_at timestamp with time zone
);


--
-- Name: tickets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tickets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tickets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tickets_id_seq OWNED BY public.tickets.id;


--
-- Name: ticket_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_events ALTER COLUMN id SET DEFAULT nextval('public.ticket_events_id_seq'::regclass);


--
-- Name: tickets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets ALTER COLUMN id SET DEFAULT nextval('public.tickets_id_seq'::regclass);


--
-- Name: ticket_events ticket_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_events
    ADD CONSTRAINT ticket_events_pkey PRIMARY KEY (id);


--
-- Name: tickets tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_pkey PRIMARY KEY (id);


--
-- Name: idx_ticket_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_events_created_at ON public.ticket_events USING btree (created_at);


--
-- Name: idx_ticket_events_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_events_event ON public.ticket_events USING btree (event);


--
-- Name: idx_ticket_events_ticket_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_events_ticket_id ON public.ticket_events USING btree (ticket_id);


--
-- Name: idx_tickets_category_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tickets_category_resource ON public.tickets USING btree (category, resource);


--
-- Name: idx_tickets_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tickets_priority ON public.tickets USING btree (priority);


--
-- Name: idx_tickets_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tickets_status ON public.tickets USING btree (status);


--
-- Name: ticket_events ticket_events_ticket_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ticket_events
    ADD CONSTRAINT ticket_events_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES public.tickets(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


