import { Injectable } from "@angular/core";
import { MetadataService } from "./metadata.service"

export const SUMMARY = 'summary';
export const DETAILS = 'details';
export const CREATE  = 'create';
export const EDIT  = 'edit';

export type ViewMode = 'summary' | 'details' | 'create' | 'edit';
@Injectable({
  providedIn: 'root'
})

export class ModeService {

    constructor(private metadataService: MetadataService){}

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
     * Gets the fields to be displayed for a foreign key field in a specific mode
     * @param entityType The entity type containing the field
     * @param fieldName The field name (typically ending with Id)
     * @param mode The mode (summary, view, edit, create)
     * @returns An array of field names to be displayed, or null if no configuration is found
     */
    getShowFields(entityType: string, fieldName: string, mode: string): string[] | null {
        // Get the show configuration from metadata service (already matched to mode)
        const showConfig = this.metadataService.getShowConfig(entityType, fieldName, mode);
        
        if (!showConfig) {
            // No show config is fine - default behavior will apply
            return null;
        }
        
        // Return the fields to display - metadata service has already matched the mode
        return showConfig.displayInfo.fields;
    }
}