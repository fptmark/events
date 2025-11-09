import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../services/auth.service';
import { ServiceMetadata } from '../services/metadata.service';

@Component({
  selector: 'app-login-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login-modal.component.html',
  styleUrls: ['./login-modal.component.css']
})
export class LoginModalComponent implements OnInit {
  showModal = false;
  authnConfig: ServiceMetadata | null = null;
  credentials: { [key: string]: string } = {};
  errorMessage = '';
  isLoading = false;

  constructor(public authService: AuthService) {}

  ngOnInit() {
    // Subscribe to auth config changes
    this.authService.authnConfig.subscribe(config => {
      this.authnConfig = config;
      this.initializeCredentials();
    });

    // Subscribe to login modal trigger
    this.authService.showLoginModal.subscribe(() => {
      if (this.authnConfig) {
        this.showModal = true;
        this.errorMessage = '';
      }
    });
  }

  /**
   * Initialize credentials object based on authn config inputs
   */
  private initializeCredentials() {
    if (this.authnConfig) {
      const fields = Object.keys(this.authnConfig.inputs);
      fields.forEach(field => {
        this.credentials[field] = '';
      });
    }
  }

  /**
   * Get input field names from authn config
   */
  getInputFields(): string[] {
    return this.authnConfig ? Object.keys(this.authnConfig.inputs) : [];
  }

  /**
   * Determine input type based on field name
   * Convention: field name containing "password" -> type="password"
   */
  getInputType(field: string): string {
    return field.toLowerCase().includes('password') ? 'password' : 'text';
  }

  /**
   * Format field name for display (capitalize first letter)
   */
  formatFieldName(field: string): string {
    return field.charAt(0).toUpperCase() + field.slice(1);
  }

  /**
   * Get the label to display (from config or default to "Login")
   */
  getLoginLabel(): string {
    return this.authnConfig?.label || 'Login';
  }

  /**
   * Check if there are multiple authn configs (show rotate icon)
   */
  hasMultipleConfigs(): boolean {
    return this.authService.hasMultipleAuthnConfigs();
  }

  /**
   * Rotate to next authn configuration
   */
  onRotateConfig() {
    this.errorMessage = '';  // Clear error when switching
    this.authService.rotateAuthnConfig();
    // Credentials will be reinitialized via authnConfig subscription
  }

  /**
   * Clear error message on keypress
   */
  onInputChange() {
    this.errorMessage = '';
  }

  /**
   * Submit login form
   */
  async onSubmit() {
    this.errorMessage = '';
    this.isLoading = true;

    try {
      await this.authService.login(this.credentials);
      // Login successful
      this.showModal = false;
      this.clearCredentials();
    } catch (error: any) {
      // Show error message - keep modal open
      console.error('Login error:', error);
      this.errorMessage = 'Login Failed.';
      // Keep modal open for retry
      this.showModal = true;
      // Clear only password field for security
      this.clearPasswordField();
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * Clear credentials after successful login
   */
  private clearCredentials() {
    const fields = Object.keys(this.credentials);
    fields.forEach(field => {
      this.credentials[field] = '';
    });
  }

  /**
   * Clear only password field after failed login
   */
  private clearPasswordField() {
    const fields = Object.keys(this.credentials);
    fields.forEach(field => {
      if (field.toLowerCase().includes('password')) {
        this.credentials[field] = '';
      }
    });
  }
}
