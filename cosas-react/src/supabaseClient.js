import { createClient } from '@supabase/supabase-js';

// Estas líneas extraen las llaves de tu archivo .env de forma segura
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

// Aquí se crea la instancia de conexión
export const supabase = createClient(supabaseUrl, supabaseAnonKey);