import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import OrgDashboard from "./pages/OrgDashboard";
import OrgOnboarding from "./pages/OrgOnboarding";
import OrgSettings from "./pages/OrgSettings";
import NewRole from "./pages/NewRole";
import RoleDetails from "./pages/RoleDetails";
import InterviewReport from "./pages/InterviewReport";
import EditRoleRubric from "./pages/EditRoleRubric";
import CandidatePortal from "./pages/CandidatePortal";
import CandidateProfile from "./pages/CandidateProfile";
import InterviewLobby from "./pages/InterviewLobby";
import LiveInterview from "./pages/LiveInterview";
import CandidateInterview from "./pages/CandidateInterview";
import InterviewComplete from "./pages/InterviewComplete";
import InviteValidation from "./pages/InviteValidation";
import PracticeInterview from "./pages/PracticeInterview";
import PracticeInterviewComplete from "./pages/PracticeInterviewComplete";
import NotFound from "./pages/NotFound";
const queryClient = new QueryClient();
const App = () => (<QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />}/>
          <Route path="/auth" element={<Auth />}/>
          <Route path="/org" element={<OrgDashboard />}/>
          <Route path="/org/onboarding" element={<OrgOnboarding />}/>
          <Route path="/org/settings" element={<OrgSettings />}/>
          <Route path="/org/new-role" element={<NewRole />}/>
          <Route path="/org/role/:roleId" element={<RoleDetails />}/>
          <Route path="/org/role/:roleId/rubric" element={<EditRoleRubric />}/>
          <Route path="/org/interview/:interviewId" element={<InterviewReport />}/>
          <Route path="/candidate/portal" element={<CandidatePortal />}/>
          <Route path="/candidate/profile" element={<CandidateProfile />}/>
          <Route path="/candidate/practice" element={<PracticeInterview />}/>
          <Route path="/candidate/practice/complete" element={<PracticeInterviewComplete />}/>
          <Route path="/candidate/:inviteId/lobby" element={<InterviewLobby />}/>
          <Route path="/candidate/:inviteId/live" element={<LiveInterview />}/>
          <Route path="/candidate/:inviteId" element={<CandidateInterview />}/>
          <Route path="/candidate/complete" element={<InterviewComplete />}/>
          <Route path="/invite/:token" element={<InviteValidation />}/>
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />}/>
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>);
export default App;
