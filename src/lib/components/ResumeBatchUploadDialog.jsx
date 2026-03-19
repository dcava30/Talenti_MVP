import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, RefreshCw, Upload, Mail, CheckCircle2, XCircle } from "lucide-react";
import { resumeBatchesApi } from "@/api/resumeBatches";
import { useToast } from "@/hooks/use-toast";

export function ResumeBatchUploadDialog({ open, onOpenChange, roleId, organisationId, onSuccess }) {
    const { toast } = useToast();
    const [batch, setBatch] = useState(null);
    const [items, setItems] = useState([]);
    const [files, setFiles] = useState([]);
    const [selectedItemIds, setSelectedItemIds] = useState([]);
    const [emailOverrides, setEmailOverrides] = useState({});
    const [isUploading, setIsUploading] = useState(false);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [isInviting, setIsInviting] = useState(false);

    const pendingItems = useMemo(() => items.filter((item) => item.parse_status === "pending"), [items]);

    useEffect(() => {
        if (!open || !batch?.id || pendingItems.length === 0) {
            return undefined;
        }
        const intervalId = window.setInterval(() => {
            loadItems(batch.id, { quiet: true });
        }, 3000);
        return () => window.clearInterval(intervalId);
    }, [open, batch?.id, pendingItems.length]);

    useEffect(() => {
        if (!open) {
            setFiles([]);
            setSelectedItemIds([]);
            setEmailOverrides({});
        }
    }, [open]);

    const ensureBatch = async () => {
        if (batch?.id) {
            return batch;
        }
        const createdBatch = await resumeBatchesApi.create({
            job_role_id: roleId,
            title: `Resume batch ${new Date().toLocaleString()}`,
        });
        setBatch(createdBatch);
        return createdBatch;
    };

    const loadItems = async (batchId, { quiet = false } = {}) => {
        if (!quiet) {
            setIsRefreshing(true);
        }
        try {
            const nextItems = await resumeBatchesApi.listItems(batchId);
            setItems(nextItems || []);
        }
        catch (error) {
            if (!quiet) {
                toast({
                    title: "Unable to refresh batch",
                    description: error.message || "Try again in a moment.",
                    variant: "destructive",
                });
            }
        }
        finally {
            if (!quiet) {
                setIsRefreshing(false);
            }
        }
    };

    const handleUploadAndProcess = async () => {
        if (!files.length || !roleId || !organisationId) {
            return;
        }
        setIsUploading(true);
        try {
            const activeBatch = await ensureBatch();
            for (const file of files) {
                const uploadTarget = await resumeBatchesApi.createItemUploadUrl(activeBatch.id, {
                    file_name: file.name,
                    content_type: file.type || "application/octet-stream",
                });
                const uploadResponse = await fetch(uploadTarget.upload_url, {
                    method: "PUT",
                    headers: {
                        "Content-Type": file.type || "application/octet-stream",
                        "x-ms-blob-type": "BlockBlob",
                    },
                    body: file,
                });
                if (!uploadResponse.ok) {
                    throw new Error(`Upload failed for ${file.name}`);
                }
            }
            await resumeBatchesApi.process(activeBatch.id);
            await loadItems(activeBatch.id);
            toast({
                title: "Resumes uploaded",
                description: "Parsing has started in the background. The review queue will update as items complete.",
            });
            onSuccess?.();
        }
        catch (error) {
            toast({
                title: "Bulk upload failed",
                description: error.message || "We could not upload and queue the resume batch.",
                variant: "destructive",
            });
        }
        finally {
            setIsUploading(false);
        }
    };

    const handleUpdateItem = async (itemId, payload) => {
        try {
            const updated = await resumeBatchesApi.updateItem(itemId, payload);
            setItems((previous) => previous.map((item) => (item.id === itemId ? updated : item)));
        }
        catch (error) {
            toast({
                title: "Update failed",
                description: error.message || "Could not update the resume item.",
                variant: "destructive",
            });
        }
    };

    const handleInviteApproved = async () => {
        if (!batch?.id) {
            return;
        }
        const itemIds = selectedItemIds.length > 0
            ? selectedItemIds
            : items.filter((item) => item.recruiter_review_status === "approved").map((item) => item.id);
        if (!itemIds.length) {
            toast({
                title: "No approved candidates selected",
                description: "Approve one or more parsed resumes before inviting them.",
                variant: "destructive",
            });
            return;
        }
        setIsInviting(true);
        try {
            await resumeBatchesApi.invite(batch.id, { item_ids: itemIds, expires_in_days: 7 });
            await loadItems(batch.id);
            toast({
                title: "Invite prep queued",
                description: "Dormant candidate accounts and invitation links are being prepared for the approved candidates.",
            });
            onSuccess?.();
        }
        catch (error) {
            toast({
                title: "Invite preparation failed",
                description: error.message || "Could not queue candidate invites.",
                variant: "destructive",
            });
        }
        finally {
            setIsInviting(false);
        }
    };

    const toggleSelected = (itemId) => {
        setSelectedItemIds((previous) => previous.includes(itemId)
            ? previous.filter((id) => id !== itemId)
            : [...previous, itemId]);
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-4xl">
                <DialogHeader>
                    <DialogTitle>Bulk Upload Resumes</DialogTitle>
                    <DialogDescription>
                        Upload resumes for this role, let the worker prefill candidate accounts, then approve who should receive a Talenti invitation.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6">
                    <div className="rounded-lg border border-border p-4">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <Input
                                type="file"
                                accept=".pdf,.doc,.docx,.txt"
                                multiple
                                onChange={(event) => setFiles(Array.from(event.target.files || []))}
                            />
                            <div className="flex gap-2">
                                <Button variant="outline" onClick={() => batch?.id && loadItems(batch.id)} disabled={!batch?.id || isRefreshing}>
                                    {isRefreshing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                                    Refresh
                                </Button>
                                <Button onClick={handleUploadAndProcess} disabled={isUploading || files.length === 0}>
                                    {isUploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                                    Upload and Parse
                                </Button>
                            </div>
                        </div>
                        {files.length > 0 && (
                            <p className="mt-3 text-sm text-muted-foreground">
                                {files.length} file{files.length === 1 ? "" : "s"} selected for this role-linked batch.
                            </p>
                        )}
                    </div>

                    <div className="rounded-lg border border-border">
                        <div className="flex items-center justify-between border-b border-border px-4 py-3">
                            <div>
                                <h3 className="font-medium">Review Queue</h3>
                                <p className="text-sm text-muted-foreground">
                                    Parsed resumes appear here for email correction, approval, and invite prep.
                                </p>
                            </div>
                            <Button variant="outline" onClick={handleInviteApproved} disabled={isInviting || items.length === 0}>
                                {isInviting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Mail className="mr-2 h-4 w-4" />}
                                Queue Invites
                            </Button>
                        </div>

                        <ScrollArea className="h-[360px]">
                            <div className="divide-y divide-border">
                                {items.length === 0 && (
                                    <div className="p-6 text-sm text-muted-foreground">
                                        Upload resumes to create a recruiter review queue for this role.
                                    </div>
                                )}
                                {items.map((item) => {
                                    const parsedReady = item.parse_status === "parsed";
                                    const needsEmail = item.parse_status === "needs_email";
                                    return (
                                        <div key={item.id} className="space-y-3 p-4">
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex items-start gap-3">
                                                    <Checkbox
                                                        checked={selectedItemIds.includes(item.id)}
                                                        onCheckedChange={() => toggleSelected(item.id)}
                                                        disabled={!parsedReady}
                                                    />
                                                    <div>
                                                        <div className="flex items-center gap-2">
                                                            <p className="font-medium">{item.candidate_name || "Unnamed candidate"}</p>
                                                            <Badge variant={parsedReady ? "default" : needsEmail ? "outline" : "secondary"}>
                                                                {item.parse_status}
                                                            </Badge>
                                                            <Badge variant="outline">{item.recruiter_review_status}</Badge>
                                                        </div>
                                                        <p className="text-sm text-muted-foreground">
                                                            {item.candidate_email || "No email extracted yet"}
                                                        </p>
                                                        {item.parse_error && (
                                                            <p className="mt-1 text-sm text-destructive">{item.parse_error}</p>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        onClick={() => handleUpdateItem(item.id, { recruiter_review_status: "approved" })}
                                                        disabled={!parsedReady}
                                                    >
                                                        <CheckCircle2 className="mr-2 h-4 w-4" />
                                                        Approve
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleUpdateItem(item.id, { recruiter_review_status: "rejected" })}
                                                    >
                                                        <XCircle className="mr-2 h-4 w-4" />
                                                        Reject
                                                    </Button>
                                                </div>
                                            </div>

                                            {(needsEmail || !item.candidate_email) && (
                                                <div className="flex gap-2">
                                                    <Input
                                                        placeholder="candidate@example.com"
                                                        value={emailOverrides[item.id] ?? item.candidate_email ?? ""}
                                                        onChange={(event) => setEmailOverrides((previous) => ({
                                                            ...previous,
                                                            [item.id]: event.target.value,
                                                        }))}
                                                    />
                                                    <Button
                                                        variant="outline"
                                                        onClick={() => handleUpdateItem(item.id, {
                                                            candidate_email: emailOverrides[item.id] ?? item.candidate_email,
                                                            recruiter_review_status: "pending_review",
                                                        })}
                                                    >
                                                        Save Email
                                                    </Button>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </ScrollArea>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Close
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
