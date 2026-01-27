import jsPDF from "jspdf";
import { interviewsApi } from "@/api/interviews";

interface ScoreDimension {
  dimension: string;
  score: number;
  weight: number | null;
  evidence: string | null;
  cited_quotes: any;
}

interface InterviewScore {
  overall_score: number | null;
  narrative_summary: string | null;
  candidate_feedback: string | null;
  anti_cheat_risk_level: string | null;
  model_version: string | null;
  created_at: string;
}

interface TranscriptSegment {
  speaker: string;
  content: string;
  start_time_ms: number;
}

interface ReportData {
  roleTitle: string;
  companyName: string;
  candidateId: string;
  interviewDate: string;
  score: InterviewScore;
  dimensions: ScoreDimension[];
  transcripts: TranscriptSegment[];
}

const formatTime = (ms: number): string => {
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
};

const formatDimension = (dim: string): string => {
  return dim
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());
};

export const fetchInterviewReportData = async (
  interviewId: string,
  roleTitle: string,
  companyName: string
): Promise<ReportData | null> => {
  try {
    // Fetch interview with application info
    const interview = await interviewsApi.getById(interviewId);
    if (!interview) {
      console.error("Failed to fetch interview:", interviewId);
      return null;
    }

    // Fetch score
    const score = await interviewsApi.getScore(interviewId);

    // Fetch dimensions
    const dimensions = await interviewsApi.listDimensions(interviewId);

    // Fetch transcripts
    const transcripts = await interviewsApi.listTranscripts(interviewId);

    const application = interview.application || interview.applications;

    return {
      roleTitle,
      companyName,
      candidateId: application?.candidate_id || "Unknown",
      interviewDate: interview.started_at || interview.ended_at || new Date().toISOString(),
      score: score || {
        overall_score: null,
        narrative_summary: null,
        candidate_feedback: null,
        anti_cheat_risk_level: null,
        model_version: null,
        created_at: new Date().toISOString(),
      },
      dimensions: dimensions || [],
      transcripts: transcripts || [],
    };
  } catch (error) {
    console.error("Error fetching report data:", error);
    return null;
  }
};

export const generateInterviewPDF = (data: ReportData): void => {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 20;
  const contentWidth = pageWidth - margin * 2;
  let yPos = margin;

  const addNewPageIfNeeded = (requiredSpace: number) => {
    if (yPos + requiredSpace > doc.internal.pageSize.getHeight() - margin) {
      doc.addPage();
      yPos = margin;
    }
  };

  // Header
  doc.setFontSize(24);
  doc.setFont("helvetica", "bold");
  doc.text("Interview Report", margin, yPos);
  yPos += 10;

  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(100);
  doc.text(`Generated: ${new Date().toLocaleDateString()}`, margin, yPos);
  yPos += 15;

  // Role & Company Info
  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(0);
  doc.text(data.roleTitle, margin, yPos);
  yPos += 6;

  doc.setFontSize(11);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(80);
  doc.text(data.companyName, margin, yPos);
  yPos += 6;
  doc.text(`Interview Date: ${new Date(data.interviewDate).toLocaleDateString()}`, margin, yPos);
  yPos += 6;
  doc.text(`Candidate ID: ${data.candidateId.slice(0, 8)}...`, margin, yPos);
  yPos += 15;

  // Overall Score Section
  if (data.score.overall_score !== null) {
    doc.setFillColor(245, 245, 250);
    doc.roundedRect(margin, yPos - 5, contentWidth, 30, 3, 3, "F");

    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0);
    doc.text("Overall Score", margin + 5, yPos + 5);

    doc.setFontSize(28);
    doc.setTextColor(59, 130, 246);
    doc.text(`${Math.round(data.score.overall_score)}%`, margin + 5, yPos + 20);

    if (data.score.anti_cheat_risk_level) {
      const riskColor = data.score.anti_cheat_risk_level === "low" ? [34, 197, 94] : 
                        data.score.anti_cheat_risk_level === "medium" ? [234, 179, 8] : [239, 68, 68];
      doc.setFontSize(10);
      doc.setTextColor(riskColor[0], riskColor[1], riskColor[2]);
      doc.text(`Risk Level: ${data.score.anti_cheat_risk_level.toUpperCase()}`, margin + 60, yPos + 15);
    }

    yPos += 35;
  }

  // Score Dimensions
  if (data.dimensions.length > 0) {
    addNewPageIfNeeded(40);
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0);
    doc.text("Score Breakdown", margin, yPos);
    yPos += 10;

    data.dimensions.forEach((dim) => {
      addNewPageIfNeeded(25);

      const scorePercent = Math.round(Number(dim.score) * 10);
      const barWidth = (scorePercent / 100) * (contentWidth - 60);

      doc.setFontSize(10);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(0);
      doc.text(formatDimension(dim.dimension), margin, yPos);

      doc.setFont("helvetica", "normal");
      doc.text(`${scorePercent}/100`, pageWidth - margin - 20, yPos);

      // Progress bar background
      doc.setFillColor(229, 231, 235);
      doc.roundedRect(margin, yPos + 2, contentWidth - 60, 4, 2, 2, "F");

      // Progress bar fill
      doc.setFillColor(59, 130, 246);
      if (barWidth > 0) {
        doc.roundedRect(margin, yPos + 2, Math.max(barWidth, 4), 4, 2, 2, "F");
      }

      yPos += 12;

      // Evidence
      if (dim.evidence) {
        doc.setFontSize(9);
        doc.setTextColor(100);
        const evidenceLines = doc.splitTextToSize(dim.evidence, contentWidth - 10);
        evidenceLines.slice(0, 2).forEach((line: string) => {
          addNewPageIfNeeded(5);
          doc.text(line, margin + 5, yPos);
          yPos += 4;
        });
        yPos += 4;
      }
    });
    yPos += 10;
  }

  // Narrative Summary
  if (data.score.narrative_summary) {
    addNewPageIfNeeded(40);
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0);
    doc.text("Summary", margin, yPos);
    yPos += 8;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(60);
    const summaryLines = doc.splitTextToSize(data.score.narrative_summary, contentWidth);
    summaryLines.forEach((line: string) => {
      addNewPageIfNeeded(6);
      doc.text(line, margin, yPos);
      yPos += 5;
    });
    yPos += 10;
  }

  // Candidate Feedback
  if (data.score.candidate_feedback) {
    addNewPageIfNeeded(40);
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0);
    doc.text("Candidate Feedback", margin, yPos);
    yPos += 8;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(60);
    const feedbackLines = doc.splitTextToSize(data.score.candidate_feedback, contentWidth);
    feedbackLines.forEach((line: string) => {
      addNewPageIfNeeded(6);
      doc.text(line, margin, yPos);
      yPos += 5;
    });
    yPos += 10;
  }

  // Transcript Section
  if (data.transcripts.length > 0) {
    doc.addPage();
    yPos = margin;

    doc.setFontSize(16);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0);
    doc.text("Interview Transcript", margin, yPos);
    yPos += 12;

    data.transcripts.forEach((segment) => {
      addNewPageIfNeeded(20);

      const timestamp = formatTime(segment.start_time_ms);
      const isAI = segment.speaker.toLowerCase() === "ai" || segment.speaker.toLowerCase() === "interviewer";

      doc.setFontSize(9);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(isAI ? 59 : 16, isAI ? 130 : 185 , isAI ? 246 : 129);
      doc.text(`[${timestamp}] ${segment.speaker}:`, margin, yPos);
      yPos += 5;

      doc.setFont("helvetica", "normal");
      doc.setTextColor(40);
      const contentLines = doc.splitTextToSize(segment.content, contentWidth - 10);
      contentLines.forEach((line: string) => {
        addNewPageIfNeeded(5);
        doc.text(line, margin + 5, yPos);
        yPos += 4;
      });
      yPos += 6;
    });
  }

  // Footer on each page
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(150);
    doc.text(
      `Page ${i} of ${totalPages} | ${data.companyName} - ${data.roleTitle}`,
      margin,
      doc.internal.pageSize.getHeight() - 10
    );
  }

  // Download
  const filename = `interview-report-${data.candidateId.slice(0, 8)}-${new Date().toISOString().split("T")[0]}.pdf`;
  doc.save(filename);
};

export const downloadInterviewReport = async (
  interviewId: string,
  roleTitle: string,
  companyName: string
): Promise<boolean> => {
  try {
    const data = await fetchInterviewReportData(interviewId, roleTitle, companyName);
    if (!data) {
      console.error("No report data available");
      return false;
    }
    generateInterviewPDF(data);
    return true;
  } catch (error) {
    console.error("Error generating PDF:", error);
    return false;
  }
};
