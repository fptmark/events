import { Injectable } from "@angular/core";

export const SUMMARY = 'summary';
export const VIEW = 'view';
export const CREATE  = 'create';
export const EDIT  = 'edit';

export type ViewMode = 'summary' | 'view' | 'create' | 'edit';
@Injectable({
  providedIn: 'root'
})

export class ViewService {


    constructor(){}

    inSummaryMode(mode: ViewMode): boolean {
        return mode === SUMMARY;
    }

    inViewMode(mode: ViewMode): boolean {
        return mode === VIEW;
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

    existsInViewMode(displayPages: string): boolean {
        return this.existsInAllModes(displayPages) || displayPages.includes(VIEW);
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

}