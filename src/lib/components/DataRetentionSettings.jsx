import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger, } from "@/components/ui/alert-dialog";
import { Trash2, Clock, Shield, AlertTriangle, CheckCircle, Loader2 } from "lucide-react";
import { useDeletionRequests, useCreateDeletionRequest } from "@/hooks/useDeletionRequests";
import { format } from "date-fns";
export const DataRetentionSettings = () => {
    const [requestType, setRequestType] = useState("full_deletion");
    const [reason, setReason] = useState("");
    const [showConfirmDialog, setShowConfirmDialog] = useState(false);
    const { data: deletionRequests, isLoading } = useDeletionRequests();
    const createRequest = useCreateDeletionRequest();
    const handleSubmitRequest = () => {
        createRequest.mutate({ requestType, reason });
        setShowConfirmDialog(false);
        setReason("");
    };
    const getStatusBadge = (status) => {
        switch (status) {
            case "pending":
                return <Badge variant="outline" className="bg-yellow-50 text-yellow-700"><Clock className="w-3 h-3 mr-1"/> Pending</Badge>;
            case "processing":
                return <Badge variant="outline" className="bg-blue-50 text-blue-700"><Loader2 className="w-3 h-3 mr-1 animate-spin"/> Processing</Badge>;
            case "completed":
                return <Badge variant="outline" className="bg-green-50 text-green-700"><CheckCircle className="w-3 h-3 mr-1"/> Completed</Badge>;
            case "failed":
                return <Badge variant="destructive"><AlertTriangle className="w-3 h-3 mr-1"/> Failed</Badge>;
            default:
                return <Badge variant="outline">{status}</Badge>;
        }
    };
    const getRequestTypeLabel = (type) => {
        switch (type) {
            case "full_deletion":
                return "Full Account Deletion";
            case "recording_only":
                return "Recording Deletion Only";
            case "anonymize":
                return "Anonymize Profile";
            default:
                return type;
        }
    };
    const hasPendingRequest = deletionRequests?.some(r => r.status === "pending" || r.status === "processing");
    return (<div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5"/>
            Data Retention & Privacy
          </CardTitle>
          <CardDescription>
            Manage your data and exercise your privacy rights. Interview recordings are automatically deleted after 30-60 days based on employer settings.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Data Retention Info */}
          <div className="p-4 bg-muted rounded-lg space-y-2">
            <h4 className="font-medium flex items-center gap-2">
              <Clock className="w-4 h-4"/>
              Automatic Data Retention
            </h4>
            <ul className="text-sm text-muted-foreground space-y-1 ml-6 list-disc">
              <li>Interview recordings: Automatically deleted after 30-60 days</li>
              <li>Transcripts and scores: Retained for application review purposes</li>
              <li>Profile data: Retained until you request deletion</li>
            </ul>
          </div>

          {/* Request Deletion */}
          <div className="space-y-4">
            <h4 className="font-medium">Request Data Deletion</h4>
            
            <RadioGroup value={requestType} onValueChange={(v) => setRequestType(v)} className="space-y-3">
              <div className="flex items-start space-x-3 p-3 border rounded-lg hover:bg-muted/50 cursor-pointer">
                <RadioGroupItem value="recording_only" id="recording_only" className="mt-1"/>
                <div className="space-y-1">
                  <Label htmlFor="recording_only" className="font-medium cursor-pointer">
                    Delete Recordings Only
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Remove all interview video/audio recordings while keeping your profile and application history.
                  </p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3 p-3 border rounded-lg hover:bg-muted/50 cursor-pointer">
                <RadioGroupItem value="anonymize" id="anonymize" className="mt-1"/>
                <div className="space-y-1">
                  <Label htmlFor="anonymize" className="font-medium cursor-pointer">
                    Anonymize Profile
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Replace your personal information with anonymous data. Your application history remains but cannot be linked to you.
                  </p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3 p-3 border border-destructive/50 rounded-lg hover:bg-destructive/5 cursor-pointer">
                <RadioGroupItem value="full_deletion" id="full_deletion" className="mt-1"/>
                <div className="space-y-1">
                  <Label htmlFor="full_deletion" className="font-medium cursor-pointer text-destructive">
                    Full Account Deletion
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Permanently delete all your data including profile, applications, interviews, and scores. This cannot be undone.
                  </p>
                </div>
              </div>
            </RadioGroup>

            <div className="space-y-2">
              <Label htmlFor="reason">Reason (optional)</Label>
              <Textarea id="reason" placeholder="Please let us know why you're requesting deletion..." value={reason} onChange={(e) => setReason(e.target.value)} rows={3}/>
            </div>

            <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
              <AlertDialogTrigger asChild>
                <Button variant={requestType === "full_deletion" ? "destructive" : "default"} disabled={hasPendingRequest || createRequest.isPending} className="w-full">
                  <Trash2 className="w-4 h-4 mr-2"/>
                  {hasPendingRequest ? "Request Already Pending" : "Submit Deletion Request"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-destructive"/>
                    Confirm Deletion Request
                  </AlertDialogTitle>
                  <AlertDialogDescription className="space-y-2">
                    <p>You are about to request: <strong>{getRequestTypeLabel(requestType)}</strong></p>
                    {requestType === "full_deletion" && (<p className="text-destructive font-medium">
                        Warning: Full deletion is permanent and cannot be undone. All your data will be removed from our systems.
                      </p>)}
                    <p>Your request will be processed within 30 days in accordance with GDPR requirements.</p>
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleSubmitRequest} className={requestType === "full_deletion" ? "bg-destructive hover:bg-destructive/90" : ""}>
                    Confirm Request
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </CardContent>
      </Card>

      {/* Previous Requests */}
      {!isLoading && deletionRequests && deletionRequests.length > 0 && (<Card>
          <CardHeader>
            <CardTitle className="text-lg">Deletion Request History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {deletionRequests.map((request) => (<div key={request.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="space-y-1">
                    <p className="font-medium">{getRequestTypeLabel(request.request_type)}</p>
                    <p className="text-sm text-muted-foreground">
                      Requested: {format(new Date(request.requested_at), "PPp")}
                    </p>
                    {request.processed_at && (<p className="text-sm text-muted-foreground">
                        Processed: {format(new Date(request.processed_at), "PPp")}
                      </p>)}
                    {request.notes && (<p className="text-sm text-destructive">{request.notes}</p>)}
                  </div>
                  <div>{getStatusBadge(request.status)}</div>
                </div>))}
            </div>
          </CardContent>
        </Card>)}
    </div>);
};
