import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Video, Users, BarChart3, Clock, Shield, Zap, User, Briefcase } from "lucide-react";

const Index = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5">
      {/* Header */}
      <header className="border-b border-border/40 backdrop-blur-sm bg-background/80 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">T</span>
            </div>
            <span className="text-xl font-bold">Talenti</span>
          </div>
          <nav className="hidden md:flex items-center gap-6">
            <Link to="/#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</Link>
            <Link to="/#how-it-works" className="text-sm text-muted-foreground hover:text-foreground transition-colors">How it Works</Link>
          </nav>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/auth">Sign In</Link>
            </Button>
            <Button size="sm" asChild>
              <Link to="/auth">Get Started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 md:py-32">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-4">
            <Zap className="w-4 h-4" />
            AI-Powered Recruitment
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
            Transform Your Hiring with
            <span className="block bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              AI-Driven Interviews
            </span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Screen candidates efficiently with live AI voice interviews, automated resume parsing, 
            and intelligent scoring. Save time, reduce bias, and hire the best talent.
          </p>
          
          {/* User Type Cards */}
          <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto pt-8">
            <Link
              to="/auth?type=candidate"
              className="group p-6 rounded-2xl bg-card border border-border hover:border-primary hover:shadow-lg transition-all"
            >
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors mx-auto">
                <User className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">I'm a Candidate</h3>
              <p className="text-muted-foreground text-sm">
                Complete interviews, manage your profile, and track applications
              </p>
            </Link>

            <Link
              to="/auth?type=organisation"
              className="group p-6 rounded-2xl bg-card border border-border hover:border-primary hover:shadow-lg transition-all"
            >
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors mx-auto">
                <Briefcase className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">I'm an Organisation</h3>
              <p className="text-muted-foreground text-sm">
                Post roles, screen candidates, and hire smarter with AI
              </p>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container mx-auto px-4 py-20 bg-card/30 rounded-3xl my-12">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">Why Choose Talenti?</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Built on Azure with enterprise-grade security and AI-powered insights
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <div className="p-6 rounded-2xl bg-background border border-border hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <Video className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Async Video Interviews</h3>
            <p className="text-muted-foreground">
              Candidates record answers at their convenience. No scheduling hassles, works globally.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-background border border-border hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <BarChart3 className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">AI-Powered Scoring</h3>
            <p className="text-muted-foreground">
              GPT-4o analyzes responses across skills, culture fit, motivation, and communication.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-background border border-border hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <Users className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Smart Resume Parsing</h3>
            <p className="text-muted-foreground">
              Bulk upload CVs and let Azure AI extract key skills, experience, and qualifications.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-background border border-border hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <Clock className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Save 80% of Screening Time</h3>
            <p className="text-muted-foreground">
              Automated transcription and analysis means you focus only on top candidates.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-background border border-border hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Enterprise Security</h3>
            <p className="text-muted-foreground">
              Azure-native with Entra ID, private endpoints, and encryption at rest.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-background border border-border hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <Zap className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Sub-$1 Per Interview</h3>
            <p className="text-muted-foreground">
              Cost-effective at scale with Azure AI Speech, Document Intelligence, and OpenAI.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="max-w-3xl mx-auto text-center space-y-6 p-12 rounded-3xl bg-gradient-to-br from-primary/10 to-primary/5 border border-primary/20">
          <h2 className="text-3xl md:text-4xl font-bold">Ready to Transform Your Hiring?</h2>
          <p className="text-lg text-muted-foreground">
            Join forward-thinking organisations using AI to find the best talent faster.
          </p>
          <Button size="lg" asChild className="text-base">
            <Link to="/org">Get Started Free</Link>
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 mt-20">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-primary flex items-center justify-center">
                <span className="text-primary-foreground text-sm font-bold">T</span>
              </div>
              <span className="font-semibold">Talenti</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2025 Talenti. Built on Azure for enterprise hiring.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
