import bcrypt from 'bcryptjs';
import { prisma } from './db/prisma';
import type { UserIdentity } from './auth';
import type { User } from '@prisma/client';

/**
 * User data structure (Prisma-generated type)
 */
export type { User };

/**
 * Finds a user by email
 * 
 * @param email - User email address
 * @returns User object or null if not found
 */
export async function findUserByEmail(email: string): Promise<User | null> {
  try {
    return await prisma.user.findUnique({
      where: {
        email: email.toLowerCase(),
      },
    });
  } catch (error) {
    console.error('Error finding user by email:', error);
    throw error;
  }
}

/**
 * Finds a user by ID
 * 
 * @param id - User ID
 * @returns User object or null if not found
 */
export async function findUserById(id: string): Promise<User | null> {
  try {
    return await prisma.user.findUnique({
      where: {
        id,
      },
    });
  } catch (error) {
    console.error('Error finding user by ID:', error);
    throw error;
  }
}

/**
 * Validates user credentials
 * 
 * @param email - User email
 * @param password - Plain text password
 * @returns User object if credentials are valid, null otherwise
 */
export async function validateCredentials(
  email: string,
  password: string
): Promise<User | null> {
  const user = await findUserByEmail(email);
  if (!user) {
    return null;
  }

  const isValid = await bcrypt.compare(password, user.passwordHash);
  if (!isValid) {
    return null;
  }

  // Update last login timestamp
  try {
    await prisma.user.update({
      where: { id: user.id },
      data: { lastLoginAt: new Date() },
    });
  } catch (error) {
    // Log but don't fail login if timestamp update fails
    console.error('Error updating lastLoginAt:', error);
  }

  return user;
}

/**
 * Converts a User object to UserIdentity
 * 
 * @param user - User object
 * @returns UserIdentity object
 */
export function userToIdentity(user: User): UserIdentity {
  return {
    user_id: user.id,
    email: user.email,
    roles: user.roles,
    permissions: user.permissions,
  };
}

/**
 * Creates a new user
 * 
 * @param email - User email
 * @param password - Plain text password
 * @param roles - User roles
 * @param permissions - User permissions
 * @param name - User name (optional)
 * @returns Created user object
 */
export async function createUser(
  email: string,
  password: string,
  roles: string[] = ['customer'],
  permissions: string[] = ['read'],
  name?: string
): Promise<User> {
  // Check if user already exists
  const existing = await findUserByEmail(email);
  if (existing) {
    throw new Error('User already exists');
  }

  const passwordHash = await bcrypt.hash(password, 10);

  try {
    return await prisma.user.create({
      data: {
        email: email.toLowerCase(),
        passwordHash,
        roles,
        permissions,
        name,
      },
    });
  } catch (error) {
    console.error('Error creating user:', error);
    throw error;
  }
}

/**
 * Update user password
 * 
 * @param userId - User ID
 * @param newPassword - New plain text password
 */
export async function updateUserPassword(
  userId: string,
  newPassword: string
): Promise<void> {
  const passwordHash = await bcrypt.hash(newPassword, 10);
  
  await prisma.user.update({
    where: { id: userId },
    data: { passwordHash },
  });
}

/**
 * Get default password for testing
 * @returns Default password string
 */
export function getDefaultPassword(): string {
  return 'password123';
}
