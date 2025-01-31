from supabase_py import Client, create_client


SUPABASE_URL= 'https://avostoupyaxiqyjnfvnj.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF2b3N0b3VweWF4aXF5am5mdm5qIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgxNDE4NzEsImV4cCI6MjA1MzcxNzg3MX0.2wnDWtzwv0IS6grzTBUEvU2a6MRzWkxICi9BGMnnbI0'


#supabase_url = 'https://grznavxjsqyvtalryrjh.supabase.co'
#supabase_key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdyem5hdnhqc3F5dnRhbHJ5cmpoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzc2MjUxNzMsImV4cCI6MjA1MzIwMTE3M30.Nz-hUGMM5G2Ccjc3K2PddQxLCUdfB1MgIAexV0OXEVM'
#supabase = create_client(supabase_url, supabase_key)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
response = (
    supabase.table("employee")
    .insert(
        [
            {
                "e_id": 1,
                "e_name": "abc",
                "email": "abc@gmail.com",
                "password": "test",
                "manager_id": 1,
            }
        ]
    )
    .execute()
)