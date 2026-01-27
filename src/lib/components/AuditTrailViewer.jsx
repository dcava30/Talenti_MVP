import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue, } from "@/components/ui/select";
import { Search, Unlock, Edit, Star, Send, Plus, Activity, Filter, Calendar, User, FileText } from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { useAuditLog, formatActionType, formatEntityType, getActionIconType } from "@/hooks/useAuditLog";
export function AuditTrailViewer({ organisationId }) {
    const { data: auditLogs, isLoading } = useAuditLog(organisationId);
    const [searchQuery, setSearchQuery] = useState("");
    const [actionFilter, setActionFilter] = useState("all");
    const [entityFilter, setEntityFilter] = useState("all");
    const getActionIcon = (action) => {
        const iconType = getActionIconType(action);
        const iconClass = "w-4 h-4";
        switch (iconType) {
            case "unlock":
                return <Unlock className={iconClass}/>;
            case "edit":
                return <Edit className={iconClass}/>;
            case "score":
                return <Star className={iconClass}/>;
            case "send":
                return <Send className={iconClass}/>;
            case "create":
                return <Plus className={iconClass}/>;
            default:
                return <Activity className={iconClass}/>;
        }
    };
    const getActionColor = (action) => {
        const iconType = getActionIconType(action);
        switch (iconType) {
            case "unlock":
                return "bg-blue-500/10 text-blue-500";
            case "edit":
                return "bg-amber-500/10 text-amber-500";
            case "score":
                return "bg-purple-500/10 text-purple-500";
            case "send":
                return "bg-green-500/10 text-green-500";
            case "create":
                return "bg-primary/10 text-primary";
            default:
                return "bg-muted text-muted-foreground";
        }
    };
    // Get unique actions and entity types for filters
    const uniqueActions = [...new Set(auditLogs?.map(log => log.action) || [])];
    const uniqueEntityTypes = [...new Set(auditLogs?.map(log => log.entity_type) || [])];
    // Filter logs
    const filteredLogs = auditLogs?.filter((log) => {
        const matchesSearch = searchQuery === "" ||
            log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
            log.entity_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (log.entity_id && log.entity_id.toLowerCase().includes(searchQuery.toLowerCase()));
        const matchesAction = actionFilter === "all" || log.action === actionFilter;
        const matchesEntity = entityFilter === "all" || log.entity_type === entityFilter;
        return matchesSearch && matchesAction && matchesEntity;
    });
    const formatChangeDetails = (log) => {
        if (!log.old_values && !log.new_values)
            return null;
        if (log.action === "score_override" && log.new_values) {
            const newScore = log.new_values.overall_score;
            const reason = log.new_values.override_reason;
            return `New score: ${newScore}${reason ? ` - "${reason}"` : ""}`;
        }
        if (log.action === "rubric_updated" && log.new_values) {
            return "Rubric weights updated";
        }
        return null;
    };
    if (isLoading) {
        return (<Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-muted rounded w-1/4"></div>
          <div className="h-12 bg-muted rounded"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (<div key={i} className="h-16 bg-muted rounded"></div>))}
          </div>
        </div>
      </Card>);
    }
    return (<Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold mb-1">Audit Trail</h2>
          <p className="text-sm text-muted-foreground">
            Track all actions taken within your organisation
          </p>
        </div>
        <Badge variant="outline" className="gap-1">
          <FileText className="w-3 h-3"/>
          {filteredLogs?.length || 0} entries
        </Badge>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"/>
          <Input placeholder="Search audit logs..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9"/>
        </div>
        
        <Select value={actionFilter} onValueChange={setActionFilter}>
          <SelectTrigger className="w-[180px]">
            <Filter className="w-4 h-4 mr-2"/>
            <SelectValue placeholder="Filter by action"/>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Actions</SelectItem>
            {uniqueActions.map((action) => (<SelectItem key={action} value={action}>
                {formatActionType(action)}
              </SelectItem>))}
          </SelectContent>
        </Select>

        <Select value={entityFilter} onValueChange={setEntityFilter}>
          <SelectTrigger className="w-[180px]">
            <Filter className="w-4 h-4 mr-2"/>
            <SelectValue placeholder="Filter by type"/>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {uniqueEntityTypes.map((entity) => (<SelectItem key={entity} value={entity}>
                {formatEntityType(entity)}
              </SelectItem>))}
          </SelectContent>
        </Select>

        {(searchQuery || actionFilter !== "all" || entityFilter !== "all") && (<Button variant="ghost" size="sm" onClick={() => {
                setSearchQuery("");
                setActionFilter("all");
                setEntityFilter("all");
            }}>
            Clear filters
          </Button>)}
      </div>

      {/* Audit Log List */}
      <ScrollArea className="h-[500px]">
        {filteredLogs && filteredLogs.length > 0 ? (<div className="space-y-3">
            {filteredLogs.map((log) => {
                const changeDetails = formatChangeDetails(log);
                return (<div key={log.id} className="flex items-start gap-4 p-4 rounded-lg border border-border hover:bg-accent/30 transition-colors">
                  <div className={`p-2 rounded-lg flex-shrink-0 ${getActionColor(log.action)}`}>
                    {getActionIcon(log.action)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">
                        {formatActionType(log.action)}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {formatEntityType(log.entity_type)}
                      </Badge>
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground mb-1">
                      {log.user_id && (<span className="flex items-center gap-1">
                          <User className="w-3 h-3"/>
                          User #{log.user_id.slice(0, 8)}
                        </span>)}
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3"/>
                        {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                      </span>
                    </div>

                    {log.entity_id && (<p className="text-xs text-muted-foreground">
                        Entity: #{log.entity_id.slice(0, 8)}
                      </p>)}
                    
                    {changeDetails && (<p className="text-sm text-muted-foreground mt-1 bg-muted/50 px-2 py-1 rounded">
                        {changeDetails}
                      </p>)}
                  </div>

                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-muted-foreground">
                      {format(new Date(log.created_at), "MMM d, yyyy")}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {format(new Date(log.created_at), "h:mm a")}
                    </p>
                  </div>
                </div>);
            })}
          </div>) : (<div className="text-center py-12">
            <Activity className="w-12 h-12 mx-auto text-muted-foreground/30 mb-4"/>
            <h3 className="text-lg font-medium mb-2">No audit logs found</h3>
            <p className="text-muted-foreground text-sm">
              {searchQuery || actionFilter !== "all" || entityFilter !== "all"
                ? "Try adjusting your filters"
                : "Actions will be logged as they occur"}
            </p>
          </div>)}
      </ScrollArea>
    </Card>);
}
