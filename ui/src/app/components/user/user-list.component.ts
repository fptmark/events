import { Component, OnInit } from '@angular/core';
import { User, UserService } from '../../services/user.service';
import { Router, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <h2>User Management</h2>
    <button (click)="navigateToCreate()">Create New User</button>
    <ul>
      <li *ngFor="let user of users; let i = index">
        {{ i + 1 }}: {{ user.username }} ({{ user.email }})
        <button (click)="editUser(user.id)">Edit</button>
        <button (click)="deleteUser(user.id)">Delete</button>
      </li>
    </ul>
  `
})
export class UserListComponent implements OnInit {
  users: User[] = [];
  constructor(private userService: UserService, private router: Router) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers() {
    this.userService.getUsers().subscribe(data => this.users = data);
  }

  navigateToCreate() {
    this.router.navigate(['/users/create']);
  }

  editUser(id: string) {
    this.router.navigate(['/users/edit', id]);
  }

  deleteUser(id: string) {
    if (confirm('Are you sure?')) {
      this.userService.deleteUser(id).subscribe(() => this.loadUsers());
    }
  }
}
