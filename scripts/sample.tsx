import React, { useState, useEffect } from "react";

interface User {
    id: number;
    name: string;
    email: string;
}

type ApiResponse = {
    success: boolean;
    data: User[];
};

class AuthService {
    login(email: string, password: string): boolean {
        return email === "admin@test.com" && password === "password";
    }

    logout(): void {
        console.log("User logged out");
    }
}

function fetchUsers(): Promise<ApiResponse> {
    return Promise.resolve({
        success: true,
        data: [
            {
                id: 1,
                name: "Kanishk",
                email: "kanishk@test.com",
            },
        ],
    });
}

const calculateAge = (birthYear: number): number => {
    return new Date().getFullYear() - birthYear;
};

export default function Dashboard() {
    const [users, setUsers] = useState<User[]>([]);

    useEffect(() => {
        fetchUsers().then((response) => {
            if (response.success) {
                setUsers(response.data);
            }
        });
    }, []);

    const authService = new AuthService();

    return (
        <div>
            <h1>Dashboard</h1>

            <button
                onClick={() =>
                    authService.login("admin@test.com", "password")
                }
            >
                Login
            </button>

            <p>Total Users: {users.length}</p>
            <p>Age Example: {calculateAge(2000)}</p>
        </div>
    );
}