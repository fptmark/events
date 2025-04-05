import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MetadataService } from './services/metadata.service'

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  template: `
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
      <div class="container-fluid">
        <a class="navbar-brand" routerLink="/">Events Management</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" 
          aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item">
              <a class="nav-link" routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}">Dashboard</a>
            </li>
            <li class="nav-item" *ngFor="let entity of metadataService.getRecent()">
              <a class="nav-link" [routerLink]="['/entity', (entity | lowercase) ]" routerLinkActive="active">
                {{ metadataService.getTitle(entity) }}
              </a>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    
    <div class="container-fluid py-3">
      <router-outlet></router-outlet>
    </div>
  `,
  styles: [`
    .container-fluid { 
      padding-left: 15px;
      padding-right: 15px; 
    }
  `]
})
export class AppComponent implements OnInit {
  title = 'Events Management';
  // recent: string[] = []

  constructor(
    public metadataService: MetadataService,
  ) {
  }

  ngOnInit() {
    // Simple initialization
    console.log('AppComponent: App initialized')
  }

  // ngAfterViewInit() {
  //   this.recent = this.metadataService.getRecent()
  // }

  // getTitle(entityType: string): string {
  //   return this.metadataService.getTitle(entityType)
  // }
}
