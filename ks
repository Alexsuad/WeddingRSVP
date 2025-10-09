                                              Table "public.guests"
        Column         |            Type             | Collation | Nullable |              Default               
-----------------------+-----------------------------+-----------+----------+------------------------------------
 id                    | integer                     |           | not null | nextval('guests_id_seq'::regclass)
 guest_code            | character varying(64)       |           | not null | 
 full_name             | character varying(120)      |           | not null | 
 email                 | character varying(254)      |           |          | 
 phone                 | character varying(32)       |           |          | 
 is_primary            | boolean                     |           |          | 
 group_id              | character varying           |           |          | 
 side                  | sideenum                    |           |          | 
 relationship          | character varying(120)      |           |          | 
 language              | languageenum                |           | not null | 
 invite_type           | invitetypeenum              |           | not null | 
 max_accomp            | integer                     |           | not null | 
 confirmed             | boolean                     |           |          | 
 confirmed_at          | timestamp without time zone |           |          | 
 num_adults            | integer                     |           | not null | 
 num_children          | integer                     |           | not null | 
 menu_choice           | character varying           |           |          | 
 allergies             | character varying           |           |          | 
 notes                 | character varying(500)      |           |          | 
 needs_accommodation   | boolean                     |           | not null | 
 needs_transport       | boolean                     |           | not null | 
 last_reminder_at      | timestamp without time zone |           |          | 
 created_at            | timestamp without time zone |           |          | now()
 updated_at            | timestamp without time zone |           |          | 
 magic_link_token      | character varying(512)      |           |          | 
 magic_link_sent_at    | timestamp without time zone |           |          | 
 magic_link_expires_at | timestamp without time zone |           |          | 
 magic_link_used_at    | timestamp without time zone |           |          | 
Indexes:
    "guests_pkey" PRIMARY KEY, btree (id)
    "ix_guests_email" UNIQUE, btree (email)
    "ix_guests_full_name" btree (full_name)
    "ix_guests_group_id" btree (group_id)
    "ix_guests_guest_code" UNIQUE, btree (guest_code)
    "ix_guests_id" btree (id)
    "ix_guests_magic_link_token" btree (magic_link_token)
    "ix_guests_phone" UNIQUE, btree (phone)
Check constraints:
    "ck_guests_email_or_phone_required" CHECK (email IS NOT NULL OR phone IS NOT NULL)
Referenced by:
    TABLE "companions" CONSTRAINT "companions_guest_id_fkey" FOREIGN KEY (guest_id) REFERENCES guests(id) ON DELETE CASCADE

