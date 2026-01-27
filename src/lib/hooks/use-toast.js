import * as React from "react";
/** Maximum number of toasts to display at once */
const TOAST_LIMIT = 1;
/** Delay in milliseconds before removing a dismissed toast from the DOM */
const TOAST_REMOVE_DELAY = 1000000;
const actionTypes = {
    ADD_TOAST: "ADD_TOAST",
    UPDATE_TOAST: "UPDATE_TOAST",
    DISMISS_TOAST: "DISMISS_TOAST",
    REMOVE_TOAST: "REMOVE_TOAST",
};
let count = 0;
/**
 * Generates a unique ID for each toast.
 * @returns A unique string ID
 */
function genId() {
    count = (count + 1) % Number.MAX_SAFE_INTEGER;
    return count.toString();
}
const toastTimeouts = new Map();
/**
 * Adds a toast to the removal queue after it's dismissed.
 * @param toastId - The ID of the toast to queue for removal
 */
const addToRemoveQueue = (toastId) => {
    if (toastTimeouts.has(toastId)) {
        return;
    }
    const timeout = setTimeout(() => {
        toastTimeouts.delete(toastId);
        dispatch({
            type: "REMOVE_TOAST",
            toastId: toastId,
        });
    }, TOAST_REMOVE_DELAY);
    toastTimeouts.set(toastId, timeout);
};
/**
 * Reducer function for managing toast state.
 *
 * @param state - Current toast state
 * @param action - Action to perform
 * @returns Updated state
 */
export const reducer = (state, action) => {
    switch (action.type) {
        case "ADD_TOAST":
            return {
                ...state,
                toasts: [action.toast, ...state.toasts].slice(0, TOAST_LIMIT),
            };
        case "UPDATE_TOAST":
            return {
                ...state,
                toasts: state.toasts.map((t) => (t.id === action.toast.id ? { ...t, ...action.toast } : t)),
            };
        case "DISMISS_TOAST": {
            const { toastId } = action;
            if (toastId) {
                addToRemoveQueue(toastId);
            }
            else {
                state.toasts.forEach((toast) => {
                    addToRemoveQueue(toast.id);
                });
            }
            return {
                ...state,
                toasts: state.toasts.map((t) => t.id === toastId || toastId === undefined
                    ? {
                        ...t,
                        open: false,
                    }
                    : t),
            };
        }
        case "REMOVE_TOAST":
            if (action.toastId === undefined) {
                return {
                    ...state,
                    toasts: [],
                };
            }
            return {
                ...state,
                toasts: state.toasts.filter((t) => t.id !== action.toastId),
            };
    }
};
const listeners = [];
let memoryState = { toasts: [] };
/**
 * Dispatches an action to update toast state and notifies all listeners.
 * @param action - The action to dispatch
 */
function dispatch(action) {
    memoryState = reducer(memoryState, action);
    listeners.forEach((listener) => {
        listener(memoryState);
    });
}
/**
 * Creates and displays a new toast notification.
 *
 * @param props - Toast properties (title, description, variant, etc.)
 * @returns Object with toast ID and control functions
 *
 * @example
 * ```ts
 * const { id, dismiss, update } = toast({
 *   title: "Success!",
 *   description: "Your changes have been saved.",
 * });
 *
 * // Later: update the toast
 * update({ description: "Updated message" });
 *
 * // Or dismiss it
 * dismiss();
 * ```
 */
function toast({ ...props }) {
    const id = genId();
    const update = (props) => dispatch({
        type: "UPDATE_TOAST",
        toast: { ...props, id },
    });
    const dismiss = () => dispatch({ type: "DISMISS_TOAST", toastId: id });
    dispatch({
        type: "ADD_TOAST",
        toast: {
            ...props,
            id,
            open: true,
            onOpenChange: (open) => {
                if (!open)
                    dismiss();
            },
        },
    });
    return {
        id: id,
        dismiss,
        update,
    };
}
/**
 * Hook for managing toast notifications in React components.
 *
 * Provides access to current toasts and functions to create/dismiss them.
 *
 * @returns Object with toasts array, toast creation function, and dismiss function
 *
 * @example
 * ```tsx
 * const { toast, dismiss, toasts } = useToast();
 *
 * const handleSuccess = () => {
 *   toast({
 *     title: "Operation complete",
 *     description: "Your data has been saved.",
 *     variant: "default",
 *   });
 * };
 *
 * const handleError = () => {
 *   toast({
 *     title: "Error",
 *     description: "Something went wrong.",
 *     variant: "destructive",
 *   });
 * };
 * ```
 */
function useToast() {
    const [state, setState] = React.useState(memoryState);
    React.useEffect(() => {
        listeners.push(setState);
        return () => {
            const index = listeners.indexOf(setState);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        };
    }, [state]);
    return {
        ...state,
        /** Creates a new toast notification */
        toast,
        /** Dismisses a specific toast or all toasts if no ID provided */
        dismiss: (toastId) => dispatch({ type: "DISMISS_TOAST", toastId }),
    };
}
export { useToast, toast };
