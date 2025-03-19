import { Component } from '@angular/core';
import { UserService, User } from '../../services/user.service';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-user-create',
  standalone: true,
  imports: [CommonModule, RouterLink, ReactiveFormsModule],
  template: `
    <h2>Create User</h2>
    <form (ngSubmit)="createUser()">
      <label>Username:</label>
      <input [(ngModel)]="user.username" name="username" requir
      <br />
      <label>Email:</label>
      <input [(ngModel)]="user.email" name="email" required />
      <br />
      <label>First Name:</label>
      <input [(ngModel)]="user.firstName" name="firstName" required />
      <br />
      <label>Last Name:</label>
      <input [(ngModel)]="user.lastName" name="lastName" required />
      <br />
      <label>Gender:</label>
      <input [(ngModel)]="user.gender" name="gender" />
      <br />
      <label>Is Admin (Account Owner):</label>
      <input type="checkbox" [(ngModel)]="user.isAccountOwner" name="isAccountOwner" />
      <br />
      <!-- Account assignment: In a real app you might show a dropdown of admin accounts if not admin -->
      <label>Account ID (if not admin):</label>
      <input [(ngModel)]="user.accountId" name="accountId" />
      <br />
      <button type="submit">Create User</button>
    </form>
  `
})
export class UserCreateComponent {
  user: User = {
    accountId: '',
    username: '',
    email: '',
    firstName: '',
    lastName: '',
    gender: 'male',
    isAccountOwner: false
  };

  constructor(private userService: UserService, private router: Router) {}

  createUser() {
    // In a real app, you might need additional logic to assign an account
    this.userService.createUser(this.user).subscribe(() => {
      this.router.navigate(['/users']);
    });
  }
}
