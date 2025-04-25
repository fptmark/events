import { Injectable } from '@angular/core';
import { Router, NavigationEnd, Event as RouterEvent } from '@angular/router';
import { filter } from 'rxjs/operators';
import { Location } from '@angular/common';

@Injectable({ providedIn: 'root' })
export class NavigationService {
  private history: string[] = [];
  private isNavigatingBack = false;

  constructor(
    private router: Router,
    private location: Location
  ) {
    // Track navigation events
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => {
        // Only add to history if not navigating back and URL is valid
        if (!this.isNavigatingBack && event.urlAfterRedirects && event.urlAfterRedirects.startsWith('/')) {
          console.log('Adding to history:', event.urlAfterRedirects);
          
          // Check for duplicates - don't add if it's the same as the last URL
          if (this.history.length === 0 || this.history[this.history.length - 1] !== event.urlAfterRedirects) {
            this.history.push(event.urlAfterRedirects);
          } else {
            console.log('Skipping duplicate URL in history');
          }
        } else if (event.urlAfterRedirects && !event.urlAfterRedirects.startsWith('/')) {
          console.warn('Invalid URL not added to history:', event.urlAfterRedirects);
        }
        this.isNavigatingBack = false; // Reset flag
      });
  }

  /**
   * Navigate back in the browser history if possible
   * Falls back to the Angular history if browser history is not available
   */
  goBack(): void {
    console.log('Navigation history:', this.history);
    
    if (this.history.length > 1) {
      this.isNavigatingBack = true;
      // Remove current URL
      this.history.pop();
      // Get previous URL
      const previousUrl = this.history[this.history.length - 1];
      
      if (previousUrl && previousUrl.startsWith('/')) {
        console.log('Navigating back to:', previousUrl);
        
        // Make sure we don't return anything from this method
        // that could be misinterpreted as an async response indicator
        this.router.navigateByUrl(previousUrl).catch(e => {
          console.error('Error navigating to previous URL:', e);
          this.location.back(); // Fallback to browser history
        });
      } else {
        console.log('Invalid previous URL or no previous URL, using location.back()', previousUrl);
        this.location.back();
      }
    } else {
      console.log('History too short, using location.back()');
      this.location.back();
    }
    
    // Explicitly return void
    return;
  }

  /**
   * Navigate to a specific URL and add it to history
   */
  navigateTo(commands: any[]): void {
    this.router.navigate(commands);
  }

  /**
   * Get the current navigation history
   */
  getHistory(): string[] {
    return [...this.history];
  }
}