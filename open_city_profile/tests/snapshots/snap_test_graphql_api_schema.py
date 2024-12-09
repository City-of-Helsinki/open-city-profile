# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['test_graphql_schema_matches_the_reference 1'] = '''type Query {
  services(offset: Int, before: String, after: String, first: Int, last: Int, clientId: String): ServiceNodeConnection
  profile(id: ID!, serviceType: ServiceType): ProfileNode
  myProfile: ProfileNode
  downloadMyProfile(authorizationCode: String!, authorizationCodeKeycloak: String): JSONString
  profiles(serviceType: ServiceType, offset: Int, before: String, after: String, first: Int, last: Int, id: [UUID!], firstName: String, lastName: String, nickname: String, nationalIdentificationNumber: String, emails_Email: String, emails_EmailType: String, emails_Primary: Boolean, emails_Verified: Boolean, phones_Phone: String, phones_PhoneType: String, phones_Primary: Boolean, addresses_Address: String, addresses_PostalCode: String, addresses_City: String, addresses_CountryCode: String, addresses_AddressType: String, addresses_Primary: Boolean, language: String, orderBy: String): ProfileNodeConnection
  claimableProfile(token: UUID!): ProfileNode
  profileWithAccessToken(token: UUID!): RestrictedProfileNode
  serviceConnectionWithUserId(userId: UUID!, serviceClientId: String!): ServiceConnectionType
  _entities(representations: [_Any!]!): [_Entity]!
  _service: _Service!
}

type ServiceNodeConnection {
  pageInfo: PageInfo!
  edges: [ServiceNodeEdge]!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

type ServiceNodeEdge {
  node: ServiceNode
  cursor: String!
}

type ServiceNode implements Node {
  id: ID!
  name: String!
  allowedDataFields(offset: Int, before: String, after: String, first: Int, last: Int): AllowedDataFieldNodeConnection!
  createdAt: DateTime!
  gdprUrl: String!
  gdprQueryScope: String!
  gdprDeleteScope: String!
  type: ServiceType @deprecated(reason: "See \'name\' field for a replacement.")
  requiresServiceConnection: Boolean!
  serviceconnectionSet(offset: Int, before: String, after: String, first: Int, last: Int): ServiceConnectionTypeConnection! @deprecated(reason: "Always returns an empty result. Getting connections for a service is not supported and there is no replacement.")
  isPureKeycloak: Boolean!
  title(language: TranslationLanguage): String
  description(language: TranslationLanguage): String
  privacyPolicyUrl(language: TranslationLanguage): String
  termsOfUseUrl(language: TranslationLanguage): String
}

interface Node {
  id: ID!
}

type AllowedDataFieldNodeConnection {
  pageInfo: PageInfo!
  edges: [AllowedDataFieldNodeEdge]!
}

type AllowedDataFieldNodeEdge {
  node: AllowedDataFieldNode
  cursor: String!
}

type AllowedDataFieldNode implements Node {
  id: ID!
  fieldName: String!
  order: Int!
  serviceSet(offset: Int, before: String, after: String, first: Int, last: Int): ServiceNodeConnection!
  label(language: TranslationLanguage): String
}

enum TranslationLanguage {
  FI
  EN
  SV
}

scalar DateTime

enum ServiceType {
  HKI_MY_DATA @deprecated(reason: "The whole ServiceType enum is deprecated and shouldn\'t be used anymore. There are different replacements in various places, depending on how this type was used.")
  BERTH @deprecated(reason: "The whole ServiceType enum is deprecated and shouldn\'t be used anymore. There are different replacements in various places, depending on how this type was used.")
  YOUTH_MEMBERSHIP @deprecated(reason: "The whole ServiceType enum is deprecated and shouldn\'t be used anymore. There are different replacements in various places, depending on how this type was used.")
  GODCHILDREN_OF_CULTURE @deprecated(reason: "The whole ServiceType enum is deprecated and shouldn\'t be used anymore. There are different replacements in various places, depending on how this type was used.")
}

type ServiceConnectionTypeConnection {
  pageInfo: PageInfo!
  edges: [ServiceConnectionTypeEdge]!
}

type ServiceConnectionTypeEdge {
  node: ServiceConnectionType
  cursor: String!
}

type ServiceConnectionType implements Node {
  service: ServiceNode!
  createdAt: DateTime!
  enabled: Boolean!
  id: ID!
}

type ProfileNode implements Node {
  firstName: String!
  lastName: String!
  nickname: String!
  language: Language
  id: ID!
  image: String @deprecated(reason: "There is no image in the Profile. This field always just returns null.")
  primaryEmail: EmailNode
  primaryPhone: PhoneNode
  primaryAddress: AddressNode
  emails(offset: Int, before: String, after: String, first: Int, last: Int): EmailNodeConnection
  phones(offset: Int, before: String, after: String, first: Int, last: Int): PhoneNodeConnection
  addresses(offset: Int, before: String, after: String, first: Int, last: Int): AddressNodeConnection
  contactMethod: ContactMethod
  loginMethods: [LoginMethodType] @deprecated(reason: "This field is deprecated, use availableLoginMethods.")
  availableLoginMethods: [LoginMethodNode]
  sensitivedata: SensitiveDataNode
  serviceConnections(offset: Int, before: String, after: String, first: Int, last: Int): ServiceConnectionTypeConnection
  verifiedPersonalInformation: VerifiedPersonalInformationNode
}

enum Language {
  FINNISH
  ENGLISH
  SWEDISH
}

type EmailNode implements Node {
  id: ID!
  primary: Boolean!
  email: String!
  emailType: EmailType
  verified: Boolean!
}

enum EmailType {
  NONE
  WORK
  PERSONAL
  OTHER
}

type PhoneNode implements Node {
  id: ID!
  primary: Boolean!
  phone: String!
  phoneType: PhoneType
}

enum PhoneType {
  NONE
  WORK
  HOME
  MOBILE
  OTHER
}

type AddressNode implements Node {
  id: ID!
  primary: Boolean!
  address: String!
  postalCode: String!
  city: String!
  countryCode: String!
  addressType: AddressType
}

enum AddressType {
  NONE
  WORK
  HOME
  OTHER
}

type EmailNodeConnection {
  pageInfo: PageInfo!
  edges: [EmailNodeEdge]!
}

type EmailNodeEdge {
  node: EmailNode
  cursor: String!
}

type PhoneNodeConnection {
  pageInfo: PageInfo!
  edges: [PhoneNodeEdge]!
}

type PhoneNodeEdge {
  node: PhoneNode
  cursor: String!
}

type AddressNodeConnection {
  pageInfo: PageInfo!
  edges: [AddressNodeEdge]!
}

type AddressNodeEdge {
  node: AddressNode
  cursor: String!
}

enum ContactMethod {
  EMAIL
  SMS
}

enum LoginMethodType {
  PASSWORD
  OTP
  SUOMI_FI
}

type LoginMethodNode {
  method: LoginMethodType!
  createdAt: DateTime
  userLabel: String
}

type SensitiveDataNode implements Node {
  id: ID!
  ssn: String!
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

type VerifiedPersonalInformationAddressNode {
  streetAddress: String!
  postalCode: String!
  postOffice: String!
}

type VerifiedPersonalInformationForeignAddressNode {
  streetAddress: String!
  additionalAddress: String!
  countryCode: String!
}

scalar JSONString

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

scalar UUID

type RestrictedProfileNode implements Node {
  firstName: String!
  lastName: String!
  nickname: String!
  language: Language
  id: ID!
  image: String @deprecated(reason: "There is no image in the Profile. This field always just returns null.")
  primaryEmail: EmailNode
  primaryPhone: PhoneNode
  primaryAddress: AddressNode
  emails(offset: Int, before: String, after: String, first: Int, last: Int): EmailNodeConnection
  phones(offset: Int, before: String, after: String, first: Int, last: Int): PhoneNodeConnection
  addresses(offset: Int, before: String, after: String, first: Int, last: Int): AddressNodeConnection
  contactMethod: ContactMethod
}

union _Entity = ProfileNode | AddressNode

scalar _Any

type _Service {
  sdl: String
}

type Mutation {
  addServiceConnection(input: AddServiceConnectionMutationInput!): AddServiceConnectionMutationPayload
  createMyProfile(input: CreateMyProfileMutationInput!): CreateMyProfileMutationPayload
  createProfile(input: CreateProfileMutationInput!): CreateProfileMutationPayload
  createOrUpdateProfileWithVerifiedPersonalInformation(input: CreateOrUpdateProfileWithVerifiedPersonalInformationMutationInput!): CreateOrUpdateProfileWithVerifiedPersonalInformationMutationPayload @deprecated(reason: "Renamed to createOrUpdateUserProfile")
  createOrUpdateUserProfile(input: CreateOrUpdateUserProfileMutationInput!): CreateOrUpdateUserProfileMutationPayload
  updateMyProfile(input: UpdateMyProfileMutationInput!): UpdateMyProfileMutationPayload
  updateProfile(input: UpdateProfileMutationInput!): UpdateProfileMutationPayload
  deleteMyProfile(input: DeleteMyProfileMutationInput!): DeleteMyProfileMutationPayload
  deleteMyServiceData(input: DeleteMyServiceDataMutationInput!): DeleteMyServiceDataMutationPayload
  claimProfile(input: ClaimProfileMutationInput!): ClaimProfileMutationPayload
  createMyProfileTemporaryReadAccessToken(input: CreateMyProfileTemporaryReadAccessTokenMutationInput!): CreateMyProfileTemporaryReadAccessTokenMutationPayload
}

type AddServiceConnectionMutationPayload {
  serviceConnection: ServiceConnectionType
  clientMutationId: String
}

input AddServiceConnectionMutationInput {
  serviceConnection: ServiceConnectionInput!
  clientMutationId: String
}

input ServiceConnectionInput {
  service: ServiceInput
  enabled: Boolean
}

input ServiceInput {
  type: ServiceType
}

type CreateMyProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

input CreateMyProfileMutationInput {
  profile: ProfileInput!
  clientMutationId: String
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
  sensitivedata: SensitiveDataFields
  updateEmails: [UpdateEmailInput]
  removeEmails: [ID]
  updatePhones: [UpdatePhoneInput]
  removePhones: [ID]
  updateAddresses: [UpdateAddressInput]
  removeAddresses: [ID]
}

input CreateEmailInput {
  primary: Boolean
  email: String!
  emailType: EmailType!
}

input CreatePhoneInput {
  primary: Boolean
  phone: String!
  phoneType: PhoneType!
}

input CreateAddressInput {
  countryCode: String
  primary: Boolean
  address: String!
  postalCode: String!
  city: String!
  addressType: AddressType!
}

input SensitiveDataFields {
  ssn: String
}

input UpdateEmailInput {
  primary: Boolean
  id: ID!
  email: String
  emailType: EmailType
}

input UpdatePhoneInput {
  primary: Boolean
  id: ID!
  phone: String
  phoneType: PhoneType
}

input UpdateAddressInput {
  countryCode: String
  primary: Boolean
  id: ID!
  address: String
  postalCode: String
  city: String
  addressType: AddressType
}

type CreateProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

input CreateProfileMutationInput {
  serviceType: ServiceType
  profile: CreateProfileInput!
  clientMutationId: String
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
  sensitivedata: SensitiveDataFields
  updateEmails: [UpdateEmailInput]
  removeEmails: [ID]
  updatePhones: [UpdatePhoneInput]
  removePhones: [ID]
  updateAddresses: [UpdateAddressInput]
  removeAddresses: [ID]
}

type CreateOrUpdateProfileWithVerifiedPersonalInformationMutationPayload {
  profile: ProfileWithVerifiedPersonalInformationOutput
}

type ProfileWithVerifiedPersonalInformationOutput implements Node {
  id: ID!
}

input CreateOrUpdateProfileWithVerifiedPersonalInformationMutationInput {
  userId: UUID!
  serviceClientId: String
  profile: ProfileWithVerifiedPersonalInformationInput!
}

input ProfileWithVerifiedPersonalInformationInput {
  firstName: String
  lastName: String
  verifiedPersonalInformation: VerifiedPersonalInformationInput
  primaryEmail: EmailInput
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

input VerifiedPersonalInformationAddressInput {
  streetAddress: String
  postalCode: String
  postOffice: String
}

input VerifiedPersonalInformationForeignAddressInput {
  streetAddress: String
  additionalAddress: String
  countryCode: String
}

input EmailInput {
  email: String!
  verified: Boolean
}

type CreateOrUpdateUserProfileMutationPayload {
  profile: ProfileNode
}

input CreateOrUpdateUserProfileMutationInput {
  userId: UUID!
  serviceClientId: String
  profile: ProfileWithVerifiedPersonalInformationInput!
}

type UpdateMyProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

input UpdateMyProfileMutationInput {
  profile: ProfileInput!
  clientMutationId: String
}

type UpdateProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

input UpdateProfileMutationInput {
  serviceType: ServiceType
  profile: UpdateProfileInput!
  clientMutationId: String
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
  sensitivedata: SensitiveDataFields
  id: ID!
  updateEmails: [UpdateEmailInput]
  removeEmails: [ID]
  updatePhones: [UpdatePhoneInput]
  removePhones: [ID]
  updateAddresses: [UpdateAddressInput]
  removeAddresses: [ID]
}

type DeleteMyProfileMutationPayload {
  results: [ServiceConnectionDeletionResult!]!
  clientMutationId: String
}

type ServiceConnectionDeletionResult {
  service: ServiceNode!
  dryRun: Boolean!
  success: Boolean!
  errors: [ServiceConnectionDeletionError!]!
}

type ServiceConnectionDeletionError {
  code: String!
  message: [TranslatedMessage!]!
}

type TranslatedMessage {
  lang: String!
  text: String!
}

input DeleteMyProfileMutationInput {
  authorizationCode: String!
  authorizationCodeKeycloak: String
  dryRun: Boolean
  clientMutationId: String
}

type DeleteMyServiceDataMutationPayload {
  result: ServiceConnectionDeletionResult!
}

input DeleteMyServiceDataMutationInput {
  authorizationCode: String!
  authorizationCodeKeycloak: String
  serviceName: String!
  dryRun: Boolean
}

type ClaimProfileMutationPayload {
  profile: ProfileNode
  clientMutationId: String
}

input ClaimProfileMutationInput {
  token: UUID!
  profile: ProfileInput
  clientMutationId: String
}

type CreateMyProfileTemporaryReadAccessTokenMutationPayload {
  temporaryReadAccessToken: TemporaryReadAccessTokenNode
  clientMutationId: String
}

type TemporaryReadAccessTokenNode {
  token: UUID!
  expiresAt: DateTime
}

input CreateMyProfileTemporaryReadAccessTokenMutationInput {
  clientMutationId: String
}'''
