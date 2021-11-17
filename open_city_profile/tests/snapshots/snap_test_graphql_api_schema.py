# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['test_graphql_schema_matches_the_reference 1'] = '''schema {
  query: Query
  mutation: Mutation
}

input AddServiceConnectionMutationInput {
  serviceConnection: ServiceConnectionInput!
  clientMutationId: String
}

type AddServiceConnectionMutationPayload {
  serviceConnection: ServiceConnectionType
  clientMutationId: String
}

type AddressNode implements Node {
  primary: Boolean!
  id: ID!
  address: String!
  postalCode: String!
  city: String!
  countryCode: String!
  addressType: AddressType
}

type AddressNodeConnection {
  pageInfo: PageInfo!
  edges: [AddressNodeEdge]!
}

type AddressNodeEdge {
  node: AddressNode
  cursor: String!
}

enum AddressType {
  NONE
  WORK
  HOME
  OTHER
}

type AllowedDataFieldNode implements Node {
  id: ID!
  fieldName: String!
  order: Int!
  serviceSet(before: String, after: String, first: Int, last: Int): ServiceNodeConnection!
  label: String
}

type AllowedDataFieldNodeConnection {
  pageInfo: PageInfo!
  edges: [AllowedDataFieldNodeEdge]!
}

type AllowedDataFieldNodeEdge {
  node: AllowedDataFieldNode
  cursor: String!
}

input ClaimProfileMutationInput {
  token: UUID!
  profile: ProfileInput
  clientMutationId: String
}

type ClaimProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

enum ContactMethod {
  EMAIL
  SMS
}

input CreateAddressInput {
  countryCode: String
  primary: Boolean
  address: String!
  postalCode: String!
  city: String!
  addressType: AddressType!
}

input CreateEmailInput {
  primary: Boolean
  email: String!
  emailType: EmailType!
}

input CreateMyProfileMutationInput {
  profile: ProfileInput!
  clientMutationId: String
}

type CreateMyProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

input CreateMyProfileTemporaryReadAccessTokenMutationInput {
  clientMutationId: String
}

type CreateMyProfileTemporaryReadAccessTokenMutationPayload {
  temporaryReadAccessToken: TemporaryReadAccessTokenNode
  clientMutationId: String
}

input CreateOrUpdateProfileWithVerifiedPersonalInformationMutationInput {
  userId: UUID!
  serviceClientId: String
  profile: ProfileWithVerifiedPersonalInformationInput!
}

type CreateOrUpdateProfileWithVerifiedPersonalInformationMutationPayload {
  profile: ProfileWithVerifiedPersonalInformationOutput
}

input CreateOrUpdateUserProfileMutationInput {
  userId: UUID!
  serviceClientId: String
  profile: ProfileWithVerifiedPersonalInformationInput!
}

type CreateOrUpdateUserProfileMutationPayload {
  profile: ProfileNode
}

input CreatePhoneInput {
  primary: Boolean
  phone: String!
  phoneType: PhoneType!
}

input CreateProfileInput {
  firstName: String
  lastName: String
  nickname: String
  image: String
  language: Language
  contactMethod: ContactMethod
  addEmails: [CreateEmailInput]
  addPhones: [CreatePhoneInput]
  addAddresses: [CreateAddressInput]
  subscriptions: [SubscriptionInputType]
  sensitivedata: SensitiveDataFields
  updateEmails: [UpdateEmailInput]
  removeEmails: [ID]
  updatePhones: [UpdatePhoneInput]
  removePhones: [ID]
  updateAddresses: [UpdateAddressInput]
  removeAddresses: [ID]
}

input CreateProfileMutationInput {
  serviceType: ServiceType
  profile: CreateProfileInput!
  clientMutationId: String
}

type CreateProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

scalar DateTime

input DeleteMyProfileMutationInput {
  authorizationCode: String!
  clientMutationId: String
}

type DeleteMyProfileMutationPayload {
  clientMutationId: String
}

input EmailInput {
  email: String!
  verified: Boolean
}

type EmailNode implements Node {
  primary: Boolean!
  id: ID!
  email: String!
  emailType: EmailType
  verified: Boolean!
}

type EmailNodeConnection {
  pageInfo: PageInfo!
  edges: [EmailNodeEdge]!
}

type EmailNodeEdge {
  node: EmailNode
  cursor: String!
}

enum EmailType {
  NONE
  WORK
  PERSONAL
  OTHER
}

scalar JSONString

enum Language {
  FINNISH
  ENGLISH
  SWEDISH
}

type Mutation {
  updateMySubscription(input: UpdateMySubscriptionMutationInput!): UpdateMySubscriptionMutationPayload
  addServiceConnection(input: AddServiceConnectionMutationInput!): AddServiceConnectionMutationPayload
  createMyProfile(input: CreateMyProfileMutationInput!): CreateMyProfileMutationPayload
  createProfile(input: CreateProfileMutationInput!): CreateProfileMutationPayload
  createOrUpdateProfileWithVerifiedPersonalInformation(input: CreateOrUpdateProfileWithVerifiedPersonalInformationMutationInput!): CreateOrUpdateProfileWithVerifiedPersonalInformationMutationPayload @deprecated(reason: "Renamed to createOrUpdateUserProfile")
  createOrUpdateUserProfile(input: CreateOrUpdateUserProfileMutationInput!): CreateOrUpdateUserProfileMutationPayload
  updateMyProfile(input: UpdateMyProfileMutationInput!): UpdateMyProfileMutationPayload
  updateProfile(input: UpdateProfileMutationInput!): UpdateProfileMutationPayload
  deleteMyProfile(input: DeleteMyProfileMutationInput!): DeleteMyProfileMutationPayload
  claimProfile(input: ClaimProfileMutationInput!): ClaimProfileMutationPayload
  createMyProfileTemporaryReadAccessToken(input: CreateMyProfileTemporaryReadAccessTokenMutationInput!): CreateMyProfileTemporaryReadAccessTokenMutationPayload
}

interface Node {
  id: ID!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

type PhoneNode implements Node {
  primary: Boolean!
  id: ID!
  phone: String!
  phoneType: PhoneType
}

type PhoneNodeConnection {
  pageInfo: PageInfo!
  edges: [PhoneNodeEdge]!
}

type PhoneNodeEdge {
  node: PhoneNode
  cursor: String!
}

enum PhoneType {
  NONE
  WORK
  HOME
  MOBILE
  OTHER
}

input ProfileInput {
  firstName: String
  lastName: String
  nickname: String
  image: String
  language: Language
  contactMethod: ContactMethod
  addEmails: [CreateEmailInput]
  addPhones: [CreatePhoneInput]
  addAddresses: [CreateAddressInput]
  subscriptions: [SubscriptionInputType]
  sensitivedata: SensitiveDataFields
  updateEmails: [UpdateEmailInput]
  removeEmails: [ID]
  updatePhones: [UpdatePhoneInput]
  removePhones: [ID]
  updateAddresses: [UpdateAddressInput]
  removeAddresses: [ID]
}

type ProfileNode implements Node {
  firstName: String!
  lastName: String!
  nickname: String!
  image: String
  language: Language
  id: ID!
  primaryEmail: EmailNode
  primaryPhone: PhoneNode
  primaryAddress: AddressNode
  emails(before: String, after: String, first: Int, last: Int): EmailNodeConnection
  phones(before: String, after: String, first: Int, last: Int): PhoneNodeConnection
  addresses(before: String, after: String, first: Int, last: Int): AddressNodeConnection
  contactMethod: ContactMethod
  sensitivedata: SensitiveDataNode
  serviceConnections(before: String, after: String, first: Int, last: Int): ServiceConnectionTypeConnection
  subscriptions(before: String, after: String, first: Int, last: Int): SubscriptionNodeConnection
  verifiedPersonalInformation: VerifiedPersonalInformationNode
}

type ProfileNodeConnection {
  pageInfo: PageInfo!
  edges: [ProfileNodeEdge]!
  count: Int!
  totalCount: Int!
}

type ProfileNodeEdge {
  node: ProfileNode
  cursor: String!
}

input ProfileWithVerifiedPersonalInformationInput {
  firstName: String
  lastName: String
  verifiedPersonalInformation: VerifiedPersonalInformationInput
  primaryEmail: EmailInput
}

type ProfileWithVerifiedPersonalInformationOutput implements Node {
  id: ID!
}

type Query {
  subscriptionTypeCategories(before: String, after: String, first: Int, last: Int): SubscriptionTypeCategoryNodeConnection
  profile(id: ID!, serviceType: ServiceType): ProfileNode
  myProfile: ProfileNode
  downloadMyProfile(authorizationCode: String!): JSONString
  profiles(serviceType: ServiceType, before: String, after: String, first: Int, last: Int, id: [UUID!], firstName: String, lastName: String, nickname: String, nationalIdentificationNumber: String, emails_Email: String, emails_EmailType: String, emails_Primary: Boolean, emails_Verified: Boolean, phones_Phone: String, phones_PhoneType: String, phones_Primary: Boolean, addresses_Address: String, addresses_PostalCode: String, addresses_City: String, addresses_CountryCode: String, addresses_AddressType: String, addresses_Primary: Boolean, language: String, enabledSubscriptions: String, orderBy: String): ProfileNodeConnection
  claimableProfile(token: UUID!): ProfileNode
  profileWithAccessToken(token: UUID!): RestrictedProfileNode
  _entities(representations: [_Any]): [_Entity]
  _service: _Service
}

type RestrictedProfileNode implements Node {
  firstName: String!
  lastName: String!
  nickname: String!
  image: String
  language: Language
  id: ID!
  primaryEmail: EmailNode
  primaryPhone: PhoneNode
  primaryAddress: AddressNode
  emails(before: String, after: String, first: Int, last: Int): EmailNodeConnection
  phones(before: String, after: String, first: Int, last: Int): PhoneNodeConnection
  addresses(before: String, after: String, first: Int, last: Int): AddressNodeConnection
  contactMethod: ContactMethod
}

input SensitiveDataFields {
  ssn: String
}

type SensitiveDataNode implements Node {
  id: ID!
  ssn: String!
}

input ServiceConnectionInput {
  service: ServiceInput
  enabled: Boolean
}

type ServiceConnectionType implements Node {
  service: ServiceNode!
  createdAt: DateTime!
  enabled: Boolean!
  id: ID!
}

type ServiceConnectionTypeConnection {
  pageInfo: PageInfo!
  edges: [ServiceConnectionTypeEdge]!
}

type ServiceConnectionTypeEdge {
  node: ServiceConnectionType
  cursor: String!
}

input ServiceInput {
  type: ServiceType
}

type ServiceNode implements Node {
  id: ID!
  name: String!
  allowedDataFields(before: String, after: String, first: Int, last: Int): AllowedDataFieldNodeConnection!
  createdAt: DateTime!
  gdprUrl: String!
  gdprQueryScope: String!
  gdprDeleteScope: String!
  serviceconnectionSet(before: String, after: String, first: Int, last: Int): ServiceConnectionTypeConnection!
  type: ServiceType @deprecated(reason: "See \'name\' field for a replacement.")
  title: String
  description: String
}

type ServiceNodeConnection {
  pageInfo: PageInfo!
  edges: [ServiceNodeEdge]!
}

type ServiceNodeEdge {
  node: ServiceNode
  cursor: String!
}

enum ServiceType {
  HKI_MY_DATA @deprecated(reason: "The whole ServiceType enum is deprecated and shouldn\'t be used anymore. There are different replacements in various places, depending on how this type was used.")
  BERTH @deprecated(reason: "The whole ServiceType enum is deprecated and shouldn\'t be used anymore. There are different replacements in various places, depending on how this type was used.")
  YOUTH_MEMBERSHIP @deprecated(reason: "The whole ServiceType enum is deprecated and shouldn\'t be used anymore. There are different replacements in various places, depending on how this type was used.")
  GODCHILDREN_OF_CULTURE @deprecated(reason: "The whole ServiceType enum is deprecated and shouldn\'t be used anymore. There are different replacements in various places, depending on how this type was used.")
}

input SubscriptionInputType {
  subscriptionTypeId: ID!
  enabled: Boolean!
}

type SubscriptionNode implements Node {
  id: ID!
  profile: ProfileNode!
  subscriptionType: SubscriptionTypeNode!
  createdAt: DateTime!
  enabled: Boolean!
}

type SubscriptionNodeConnection {
  pageInfo: PageInfo!
  edges: [SubscriptionNodeEdge]!
}

type SubscriptionNodeEdge {
  node: SubscriptionNode
  cursor: String!
}

type SubscriptionTypeCategoryNode implements Node {
  id: ID!
  code: String!
  createdAt: DateTime!
  order: Int!
  subscriptionTypes(before: String, after: String, first: Int, last: Int): SubscriptionTypeNodeConnection!
  label: String
}

type SubscriptionTypeCategoryNodeConnection {
  pageInfo: PageInfo!
  edges: [SubscriptionTypeCategoryNodeEdge]!
}

type SubscriptionTypeCategoryNodeEdge {
  node: SubscriptionTypeCategoryNode
  cursor: String!
}

type SubscriptionTypeNode implements Node {
  id: ID!
  subscriptionTypeCategory: SubscriptionTypeCategoryNode!
  code: String!
  createdAt: DateTime!
  order: Int!
  label: String
}

type SubscriptionTypeNodeConnection {
  pageInfo: PageInfo!
  edges: [SubscriptionTypeNodeEdge]!
}

type SubscriptionTypeNodeEdge {
  node: SubscriptionTypeNode
  cursor: String!
}

type TemporaryReadAccessTokenNode {
  token: UUID!
  expiresAt: DateTime
}

scalar UUID

input UpdateAddressInput {
  countryCode: String
  primary: Boolean
  id: ID!
  address: String
  postalCode: String
  city: String
  addressType: AddressType
}

input UpdateEmailInput {
  primary: Boolean
  id: ID!
  email: String
  emailType: EmailType
}

input UpdateMyProfileMutationInput {
  profile: ProfileInput!
  clientMutationId: String
}

type UpdateMyProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

input UpdateMySubscriptionMutationInput {
  subscription: SubscriptionInputType!
  clientMutationId: String
}

type UpdateMySubscriptionMutationPayload {
  subscription: SubscriptionNode
  clientMutationId: String
}

input UpdatePhoneInput {
  primary: Boolean
  id: ID!
  phone: String
  phoneType: PhoneType
}

input UpdateProfileInput {
  firstName: String
  lastName: String
  nickname: String
  image: String
  language: Language
  contactMethod: ContactMethod
  addEmails: [CreateEmailInput]
  addPhones: [CreatePhoneInput]
  addAddresses: [CreateAddressInput]
  subscriptions: [SubscriptionInputType]
  sensitivedata: SensitiveDataFields
  id: ID!
  updateEmails: [UpdateEmailInput]
  removeEmails: [ID]
  updatePhones: [UpdatePhoneInput]
  removePhones: [ID]
  updateAddresses: [UpdateAddressInput]
  removeAddresses: [ID]
}

input UpdateProfileMutationInput {
  serviceType: ServiceType
  profile: UpdateProfileInput!
  clientMutationId: String
}

type UpdateProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

input VerifiedPersonalInformationAddressInput {
  streetAddress: String
  postalCode: String
  postOffice: String
}

type VerifiedPersonalInformationAddressNode {
  streetAddress: String!
  postalCode: String!
  postOffice: String!
}

input VerifiedPersonalInformationForeignAddressInput {
  streetAddress: String
  additionalAddress: String
  countryCode: String
}

type VerifiedPersonalInformationForeignAddressNode {
  streetAddress: String!
  additionalAddress: String!
  countryCode: String!
}

input VerifiedPersonalInformationInput {
  firstName: String
  lastName: String
  givenName: String
  nationalIdentificationNumber: String
  municipalityOfResidence: String
  municipalityOfResidenceNumber: String
  permanentAddress: VerifiedPersonalInformationAddressInput
  temporaryAddress: VerifiedPersonalInformationAddressInput
  permanentForeignAddress: VerifiedPersonalInformationForeignAddressInput
}

type VerifiedPersonalInformationNode {
  firstName: String!
  lastName: String!
  givenName: String!
  nationalIdentificationNumber: String!
  municipalityOfResidence: String!
  municipalityOfResidenceNumber: String!
  permanentAddress: VerifiedPersonalInformationAddressNode
  temporaryAddress: VerifiedPersonalInformationAddressNode
  permanentForeignAddress: VerifiedPersonalInformationForeignAddressNode
}

scalar _Any

union _Entity = AddressNode | ProfileNode

type _Service {
  sdl: String
}
'''
