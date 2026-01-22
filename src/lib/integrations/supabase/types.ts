export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "13.0.5"
  }
  public: {
    Tables: {
      applications: {
        Row: {
          candidate_id: string
          created_at: string
          id: string
          job_role_id: string
          match_score: number | null
          status: string
          updated_at: string
        }
        Insert: {
          candidate_id: string
          created_at?: string
          id?: string
          job_role_id: string
          match_score?: number | null
          status?: string
          updated_at?: string
        }
        Update: {
          candidate_id?: string
          created_at?: string
          id?: string
          job_role_id?: string
          match_score?: number | null
          status?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "applications_job_role_id_fkey"
            columns: ["job_role_id"]
            isOneToOne: false
            referencedRelation: "job_roles"
            referencedColumns: ["id"]
          },
        ]
      }
      audit_log: {
        Row: {
          action: string
          created_at: string
          entity_id: string | null
          entity_type: string
          id: string
          ip_address: string | null
          new_values: Json | null
          old_values: Json | null
          organisation_id: string | null
          user_id: string | null
        }
        Insert: {
          action: string
          created_at?: string
          entity_id?: string | null
          entity_type: string
          id?: string
          ip_address?: string | null
          new_values?: Json | null
          old_values?: Json | null
          organisation_id?: string | null
          user_id?: string | null
        }
        Update: {
          action?: string
          created_at?: string
          entity_id?: string | null
          entity_type?: string
          id?: string
          ip_address?: string | null
          new_values?: Json | null
          old_values?: Json | null
          organisation_id?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "audit_log_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisations"
            referencedColumns: ["id"]
          },
        ]
      }
      candidate_dei: {
        Row: {
          created_at: string
          disability_status: string | null
          ethnicity: string | null
          gender: string | null
          id: string
          user_id: string
          veteran_status: string | null
        }
        Insert: {
          created_at?: string
          disability_status?: string | null
          ethnicity?: string | null
          gender?: string | null
          id?: string
          user_id: string
          veteran_status?: string | null
        }
        Update: {
          created_at?: string
          disability_status?: string | null
          ethnicity?: string | null
          gender?: string | null
          id?: string
          user_id?: string
          veteran_status?: string | null
        }
        Relationships: []
      }
      candidate_profiles: {
        Row: {
          availability: string | null
          country: string | null
          created_at: string
          cv_file_path: string | null
          cv_uploaded_at: string | null
          email: string | null
          first_name: string | null
          gpa_wam: number | null
          id: string
          last_name: string | null
          linkedin_url: string | null
          paused_at: string | null
          phone: string | null
          portfolio_url: string | null
          postcode: string | null
          profile_visibility: string | null
          state: string | null
          suburb: string | null
          updated_at: string
          user_id: string
          visibility_settings: Json | null
          work_mode: string | null
          work_rights: string | null
        }
        Insert: {
          availability?: string | null
          country?: string | null
          created_at?: string
          cv_file_path?: string | null
          cv_uploaded_at?: string | null
          email?: string | null
          first_name?: string | null
          gpa_wam?: number | null
          id?: string
          last_name?: string | null
          linkedin_url?: string | null
          paused_at?: string | null
          phone?: string | null
          portfolio_url?: string | null
          postcode?: string | null
          profile_visibility?: string | null
          state?: string | null
          suburb?: string | null
          updated_at?: string
          user_id: string
          visibility_settings?: Json | null
          work_mode?: string | null
          work_rights?: string | null
        }
        Update: {
          availability?: string | null
          country?: string | null
          created_at?: string
          cv_file_path?: string | null
          cv_uploaded_at?: string | null
          email?: string | null
          first_name?: string | null
          gpa_wam?: number | null
          id?: string
          last_name?: string | null
          linkedin_url?: string | null
          paused_at?: string | null
          phone?: string | null
          portfolio_url?: string | null
          postcode?: string | null
          profile_visibility?: string | null
          state?: string | null
          suburb?: string | null
          updated_at?: string
          user_id?: string
          visibility_settings?: Json | null
          work_mode?: string | null
          work_rights?: string | null
        }
        Relationships: []
      }
      candidate_skills: {
        Row: {
          created_at: string
          id: string
          proficiency_level: string | null
          skill_name: string
          skill_type: string
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          proficiency_level?: string | null
          skill_name: string
          skill_type: string
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          proficiency_level?: string | null
          skill_name?: string
          skill_type?: string
          user_id?: string
        }
        Relationships: []
      }
      data_deletion_requests: {
        Row: {
          id: string
          notes: string | null
          processed_at: string | null
          processed_by: string | null
          reason: string | null
          request_type: string
          requested_at: string
          status: string
          user_id: string
        }
        Insert: {
          id?: string
          notes?: string | null
          processed_at?: string | null
          processed_by?: string | null
          reason?: string | null
          request_type?: string
          requested_at?: string
          status?: string
          user_id: string
        }
        Update: {
          id?: string
          notes?: string | null
          processed_at?: string | null
          processed_by?: string | null
          reason?: string | null
          request_type?: string
          requested_at?: string
          status?: string
          user_id?: string
        }
        Relationships: []
      }
      education: {
        Row: {
          created_at: string
          degree: string
          end_date: string | null
          field_of_study: string | null
          id: string
          institution: string
          is_current: boolean | null
          start_date: string | null
          user_id: string
        }
        Insert: {
          created_at?: string
          degree: string
          end_date?: string | null
          field_of_study?: string | null
          id?: string
          institution: string
          is_current?: boolean | null
          start_date?: string | null
          user_id: string
        }
        Update: {
          created_at?: string
          degree?: string
          end_date?: string | null
          field_of_study?: string | null
          id?: string
          institution?: string
          is_current?: boolean | null
          start_date?: string | null
          user_id?: string
        }
        Relationships: []
      }
      employment_history: {
        Row: {
          company_name: string
          created_at: string
          description: string | null
          end_date: string | null
          id: string
          is_current: boolean | null
          job_title: string
          start_date: string
          user_id: string
        }
        Insert: {
          company_name: string
          created_at?: string
          description?: string | null
          end_date?: string | null
          id?: string
          is_current?: boolean | null
          job_title: string
          start_date: string
          user_id: string
        }
        Update: {
          company_name?: string
          created_at?: string
          description?: string | null
          end_date?: string | null
          id?: string
          is_current?: boolean | null
          job_title?: string
          start_date?: string
          user_id?: string
        }
        Relationships: []
      }
      interview_scores: {
        Row: {
          anti_cheat_risk_level: string | null
          candidate_feedback: string | null
          created_at: string
          human_override: boolean | null
          human_override_by: string | null
          human_override_reason: string | null
          id: string
          interview_id: string
          model_version: string | null
          narrative_summary: string | null
          overall_score: number | null
          prompt_version: string | null
          rubric_version: string | null
          scored_by: string | null
          updated_at: string
        }
        Insert: {
          anti_cheat_risk_level?: string | null
          candidate_feedback?: string | null
          created_at?: string
          human_override?: boolean | null
          human_override_by?: string | null
          human_override_reason?: string | null
          id?: string
          interview_id: string
          model_version?: string | null
          narrative_summary?: string | null
          overall_score?: number | null
          prompt_version?: string | null
          rubric_version?: string | null
          scored_by?: string | null
          updated_at?: string
        }
        Update: {
          anti_cheat_risk_level?: string | null
          candidate_feedback?: string | null
          created_at?: string
          human_override?: boolean | null
          human_override_by?: string | null
          human_override_reason?: string | null
          id?: string
          interview_id?: string
          model_version?: string | null
          narrative_summary?: string | null
          overall_score?: number | null
          prompt_version?: string | null
          rubric_version?: string | null
          scored_by?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "interview_scores_interview_id_fkey"
            columns: ["interview_id"]
            isOneToOne: true
            referencedRelation: "interviews"
            referencedColumns: ["id"]
          },
        ]
      }
      interviews: {
        Row: {
          anti_cheat_signals: Json | null
          application_id: string
          created_at: string
          duration_seconds: number | null
          ended_at: string | null
          id: string
          metadata: Json | null
          recording_deleted_at: string | null
          recording_url: string | null
          started_at: string | null
          status: Database["public"]["Enums"]["interview_status"]
          updated_at: string
        }
        Insert: {
          anti_cheat_signals?: Json | null
          application_id: string
          created_at?: string
          duration_seconds?: number | null
          ended_at?: string | null
          id?: string
          metadata?: Json | null
          recording_deleted_at?: string | null
          recording_url?: string | null
          started_at?: string | null
          status?: Database["public"]["Enums"]["interview_status"]
          updated_at?: string
        }
        Update: {
          anti_cheat_signals?: Json | null
          application_id?: string
          created_at?: string
          duration_seconds?: number | null
          ended_at?: string | null
          id?: string
          metadata?: Json | null
          recording_deleted_at?: string | null
          recording_url?: string | null
          started_at?: string | null
          status?: Database["public"]["Enums"]["interview_status"]
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "interviews_application_id_fkey"
            columns: ["application_id"]
            isOneToOne: false
            referencedRelation: "applications"
            referencedColumns: ["id"]
          },
        ]
      }
      invitations: {
        Row: {
          application_id: string
          created_at: string
          email_template: string | null
          expires_at: string
          id: string
          opened_at: string | null
          sent_at: string | null
          status: Database["public"]["Enums"]["invitation_status"]
          token: string
        }
        Insert: {
          application_id: string
          created_at?: string
          email_template?: string | null
          expires_at: string
          id?: string
          opened_at?: string | null
          sent_at?: string | null
          status?: Database["public"]["Enums"]["invitation_status"]
          token: string
        }
        Update: {
          application_id?: string
          created_at?: string
          email_template?: string | null
          expires_at?: string
          id?: string
          opened_at?: string | null
          sent_at?: string | null
          status?: Database["public"]["Enums"]["invitation_status"]
          token?: string
        }
        Relationships: [
          {
            foreignKeyName: "invitations_application_id_fkey"
            columns: ["application_id"]
            isOneToOne: false
            referencedRelation: "applications"
            referencedColumns: ["id"]
          },
        ]
      }
      job_roles: {
        Row: {
          created_at: string
          created_by: string | null
          department: string | null
          description: string | null
          employment_type: string | null
          id: string
          industry: string | null
          interview_structure: Json | null
          location: string | null
          organisation_id: string
          requirements: Json | null
          salary_range_max: number | null
          salary_range_min: number | null
          scoring_rubric: Json | null
          status: Database["public"]["Enums"]["job_role_status"]
          title: string
          updated_at: string
          work_type: string | null
        }
        Insert: {
          created_at?: string
          created_by?: string | null
          department?: string | null
          description?: string | null
          employment_type?: string | null
          id?: string
          industry?: string | null
          interview_structure?: Json | null
          location?: string | null
          organisation_id: string
          requirements?: Json | null
          salary_range_max?: number | null
          salary_range_min?: number | null
          scoring_rubric?: Json | null
          status?: Database["public"]["Enums"]["job_role_status"]
          title: string
          updated_at?: string
          work_type?: string | null
        }
        Update: {
          created_at?: string
          created_by?: string | null
          department?: string | null
          description?: string | null
          employment_type?: string | null
          id?: string
          industry?: string | null
          interview_structure?: Json | null
          location?: string | null
          organisation_id?: string
          requirements?: Json | null
          salary_range_max?: number | null
          salary_range_min?: number | null
          scoring_rubric?: Json | null
          status?: Database["public"]["Enums"]["job_role_status"]
          title?: string
          updated_at?: string
          work_type?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "job_roles_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisations"
            referencedColumns: ["id"]
          },
        ]
      }
      org_users: {
        Row: {
          created_at: string
          id: string
          organisation_id: string
          role: string
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          organisation_id: string
          role?: string
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          organisation_id?: string
          role?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "org_users_organisation_id_fkey"
            columns: ["organisation_id"]
            isOneToOne: false
            referencedRelation: "organisations"
            referencedColumns: ["id"]
          },
        ]
      }
      organisations: {
        Row: {
          billing_address: string | null
          billing_email: string | null
          created_at: string
          description: string | null
          id: string
          industry: string | null
          logo_url: string | null
          name: string
          recording_retention_days: number | null
          updated_at: string
          values_framework: Json | null
          website: string | null
        }
        Insert: {
          billing_address?: string | null
          billing_email?: string | null
          created_at?: string
          description?: string | null
          id?: string
          industry?: string | null
          logo_url?: string | null
          name: string
          recording_retention_days?: number | null
          updated_at?: string
          values_framework?: Json | null
          website?: string | null
        }
        Update: {
          billing_address?: string | null
          billing_email?: string | null
          created_at?: string
          description?: string | null
          id?: string
          industry?: string | null
          logo_url?: string | null
          name?: string
          recording_retention_days?: number | null
          updated_at?: string
          values_framework?: Json | null
          website?: string | null
        }
        Relationships: []
      }
      practice_interviews: {
        Row: {
          created_at: string
          duration_seconds: number | null
          ended_at: string | null
          feedback: Json | null
          id: string
          sample_role_type: string
          started_at: string | null
          status: string
          user_id: string
        }
        Insert: {
          created_at?: string
          duration_seconds?: number | null
          ended_at?: string | null
          feedback?: Json | null
          id?: string
          sample_role_type: string
          started_at?: string | null
          status?: string
          user_id: string
        }
        Update: {
          created_at?: string
          duration_seconds?: number | null
          ended_at?: string | null
          feedback?: Json | null
          id?: string
          sample_role_type?: string
          started_at?: string | null
          status?: string
          user_id?: string
        }
        Relationships: []
      }
      score_dimensions: {
        Row: {
          cited_quotes: Json | null
          created_at: string
          dimension: string
          evidence: string | null
          id: string
          interview_id: string
          score: number
          weight: number | null
        }
        Insert: {
          cited_quotes?: Json | null
          created_at?: string
          dimension: string
          evidence?: string | null
          id?: string
          interview_id: string
          score: number
          weight?: number | null
        }
        Update: {
          cited_quotes?: Json | null
          created_at?: string
          dimension?: string
          evidence?: string | null
          id?: string
          interview_id?: string
          score?: number
          weight?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "score_dimensions_interview_id_fkey"
            columns: ["interview_id"]
            isOneToOne: false
            referencedRelation: "interviews"
            referencedColumns: ["id"]
          },
        ]
      }
      transcript_segments: {
        Row: {
          confidence: number | null
          content: string
          created_at: string
          end_time_ms: number | null
          id: string
          interview_id: string
          speaker: string
          start_time_ms: number
        }
        Insert: {
          confidence?: number | null
          content: string
          created_at?: string
          end_time_ms?: number | null
          id?: string
          interview_id: string
          speaker: string
          start_time_ms: number
        }
        Update: {
          confidence?: number | null
          content?: string
          created_at?: string
          end_time_ms?: number | null
          id?: string
          interview_id?: string
          speaker?: string
          start_time_ms?: number
        }
        Relationships: [
          {
            foreignKeyName: "transcript_segments_interview_id_fkey"
            columns: ["interview_id"]
            isOneToOne: false
            referencedRelation: "interviews"
            referencedColumns: ["id"]
          },
        ]
      }
      user_roles: {
        Row: {
          created_at: string
          id: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          role: Database["public"]["Enums"]["app_role"]
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      get_user_org_id: { Args: { _user_id: string }; Returns: string }
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
      user_belongs_to_org: {
        Args: { _org_id: string; _user_id: string }
        Returns: boolean
      }
      user_org_role: {
        Args: { _org_id: string; _user_id: string }
        Returns: string
      }
    }
    Enums: {
      app_role: "org_admin" | "org_recruiter" | "org_viewer" | "candidate"
      interview_status:
        | "invited"
        | "scheduled"
        | "in_progress"
        | "completed"
        | "cancelled"
        | "expired"
      invitation_status:
        | "pending"
        | "sent"
        | "delivered"
        | "opened"
        | "bounced"
        | "expired"
      job_role_status: "draft" | "active" | "paused" | "closed"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["org_admin", "org_recruiter", "org_viewer", "candidate"],
      interview_status: [
        "invited",
        "scheduled",
        "in_progress",
        "completed",
        "cancelled",
        "expired",
      ],
      invitation_status: [
        "pending",
        "sent",
        "delivered",
        "opened",
        "bounced",
        "expired",
      ],
      job_role_status: ["draft", "active", "paused", "closed"],
    },
  },
} as const
