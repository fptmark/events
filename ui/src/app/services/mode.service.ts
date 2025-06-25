import { Injectable } from "@angular/core";

export const SUMMARY = 'summary';
export const DETAILS = 'details';
export const CREATE  = 'create';
export const EDIT  = 'edit';

export type ViewMode = 'summary' | 'details' | 'create' | 'edit';

@Injectable({
  providedIn: 'root'
})
export class ModeService {

    constructor(){}

    inSummaryMode(mode: ViewMode): boolean {
        return mode === SUMMARY;
    }

    inDetailsMode(mode: ViewMode): boolean {
        return mode === DETAILS;
    }

    inCreateMode(mode: ViewMode): boolean {
        return mode === CREATE;
    }

    inEditMode(mode: ViewMode): boolean {
        return mode === EDIT;
    }

    existsInSummaryMode(displayPages: ViewMode): boolean {
        return this.existsInAllModes(displayPages) || displayPages.includes(SUMMARY);
    }

    existsInDetailsMode(displayPages: string): boolean {
        return this.existsInAllModes(displayPages) || displayPages.includes(DETAILS);
    }

    existsInCreateMode(displayPages: string): boolean {
        return this.existsInAllModes(displayPages) || displayPages.includes(CREATE);
    }
    
    existsInEditMode(displayPages: string): boolean {
        return this.existsInAllModes(displayPages) || displayPages.includes(EDIT);
    }

    existsInMode(displayPages: string | undefined, mode: string): boolean {
        return !displayPages || this.existsInAllModes(displayPages) || displayPages.includes(mode);
        // return this.existsInAllModes(displayPages) || displayPages?.includes(mode) || true
    }

    private existsInAllModes(displayPages: string | undefined): boolean {
        return displayPages === 'all' || displayPages === '' || displayPages === undefined; 
    }

    /**
     * Get the fields that should be displayed for an entity in a specific mode
     * @param metadata The entity metadata
     * @param currentMode The current mode (summary, details, edit, create)
     * @returns An array of field names to display
     */
    getViewFields(metadata: any, currentMode: string): string[] {
        const allFields: string[] = Object.keys(metadata.fields);

        const visibleFields = allFields.filter(field => {
            const fieldMetadata = metadata.fields[field];
            // Skip hidden fields
            if (fieldMetadata?.ui?.display === 'hidden') {
                return false;
            }
            
            // For edit and create modes, always include required fields regardless of displayPages
            if ((currentMode === EDIT || currentMode === CREATE) && fieldMetadata?.required) {
                return true;
            }
            
            // Use mode logic to determine if field is visible in current mode
            const displayPages = fieldMetadata?.ui?.displayPages ?? '';
            return this.existsInMode(displayPages, currentMode);
        });

        return visibleFields;
    }
}