import { createClient } from "@supabase/supabase-js";

const supabaseUrl = "https://jepqvwtwlhylmqilucat.supabase.co";
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImplcHF2d3R3bGh5bG1xaWx1Y2F0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA1NjM1NzksImV4cCI6MjA5NjEzOTU3OX0.9QcKhdHHS0SwzDrMCPTmn7XXt0eMNSBekpLcUUGS-iI";

export const supabase = createClient(supabaseUrl, supabaseKey);